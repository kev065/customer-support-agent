from typing import List, Annotated

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
import logging
from copilotkit import CopilotKitState

from agent.tools import all_tools
from agent.config import settings
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from copilotkit import CopilotKitState

from agent.tools import all_tools
from agent.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(CopilotKitState):
    messages: Annotated[List[BaseMessage], add_messages]


def get_llm():
    """Initializes the LLM used by the agent."""
    return ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4-turbo", temperature=0)


def get_embeddings():
    """Return an embeddings object compatible with the rest of the code.

    The sync script expects an object with an `embed_query(text)` method.
    `OpenAIEmbeddings` from `langchain_openai` provides `embed_query`, so we
    return an instance configured with the project's OpenAI key.
    """
    return OpenAIEmbeddings(api_key=settings.openai_api_key)


def chat_node(state: AgentState, config: RunnableConfig):
    """Main chat node. Calls the LLM (with tools bound) and decides next step."""
    model = get_llm()

    # Get CopilotKit frontend actions
    copilot_actions = state.get("copilotkit", {}).get("actions", []) or []
    tools = [*all_tools, *copilot_actions]
    model_with_tools = model.bind_tools(tools)

    # Add system message to the conversation
    system_message = SystemMessage(content="You are a helpful customer support assistant. Use tools when necessary to answer user queries, for example product search or order lookup.")

    messages_to_send = [system_message] + state.get("messages", [])
    response = model_with_tools.invoke(messages_to_send, config)

    return {"messages": [response]}

def create_agent_graph():
    """Builds and compiles the LangGraph StateGraph for the agent."""
    from langgraph.prebuilt import ToolNode, tools_condition
    
    # Create the graph with our custom state
    graph = StateGraph(AgentState)
    
    # Add the chat node
    graph.add_node("chat_node", chat_node)
    
    # Create and add the tool node using LangGraph's prebuilt ToolNode
    tool_node = ToolNode(all_tools)
    graph.add_node("tools", tool_node)
    
    # Set the entry point
    graph.add_edge(START, "chat_node")
    
    graph.add_conditional_edges(
        "chat_node",
        tools_condition,
        path_map=["tools", END]
    )
    
    graph.add_edge("tools", "chat_node")
    
    # Use MemorySaver for checkpointing
    runnable = graph.compile(checkpointer=MemorySaver())
    return runnable
