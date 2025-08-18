
from typing import List

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from copilotkit import CopilotKitState

from agent.tools import all_tools
from agent.config import settings


# AgentState inherits from CopilotKitState so CopilotKit actions are available
class AgentState(CopilotKitState):
    messages: List[BaseMessage] = []


def get_llm():
    """Initializes the LLM used by the agent."""
    return ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4-turbo", temperature=0)


async def chat_node(state: AgentState, config: RunnableConfig) -> Command:
    """Main chat node. Calls the LLM (with tools bound) and decides next step.

    If the model emits a tool call the node will return a Command sending the
    state to the `tool_node`. Otherwise it ends the run and returns the final
    messages so they are persisted.
    """
    model = get_llm()

    # Combine user-defined tools with any CopilotKit actions available in state
    copilot_actions = state.get("copilotkit", {}).get("actions", []) or []
    tools = [*all_tools, *copilot_actions]
    model_with_tools = model.bind_tools(tools)

    system_message = SystemMessage(content="You are a helpful customer support assistant. Use tools when necessary to answer user queries, for example product search or order lookup.")

    # Call the model and get a response which may contain tool calls
    response = await model_with_tools.ainvoke([
        system_message,
        *state["messages"],
    ], config)

    # If the model returned a message with tool calls, route to the tool runner
    if isinstance(response, AIMessage) and getattr(response, "tool_calls", None):
        # Persist the LLM response which contains the tool call(s)
        return Command(goto="tool_node", update={"messages": response})

    # No tool call: end the agent and persist the messages
    return Command(goto=END, update={"messages": response})


async def tool_node(state: AgentState, config: RunnableConfig) -> Command:
    """Executes tool calls emitted by the model and returns outputs back to the agent.

    This node inspects the last message for tool_calls, executes each matching
    tool from `all_tools`, collects results and returns a new AIMessage with
    the tool outputs so the LLM can incorporate them on the next turn.
    """
    # Get the last message which should contain the tool call(s)
    last_message = state["messages"][-1]

    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return Command(goto=END, update={"messages": last_message})

    outputs: List[str] = []

    for tc in tool_calls:
        name = tc.get("name")
        args = tc.get("args") or tc.get("input")

        # Find the tool by name
        tool = next((t for t in all_tools if getattr(t, "name", None) == name), None)
        if not tool:
            outputs.append(f"No tool named '{name}' registered.")
            continue

        try:
            # Prefer async run if available
            if hasattr(tool, "arun"):
                if isinstance(args, dict):
                    result = await tool.arun(**args)
                else:
                    result = await tool.arun(args)
            else:
                if isinstance(args, dict):
                    result = tool.run(**args)
                else:
                    result = tool.run(args)

            outputs.append(str(result))
        except Exception as e:
            outputs.append(f"Error running tool '{name}': {e}")

    # Create a single AIMessage containing concatenated tool outputs so the LLM
    # can read them on the next turn.
    combined = "\n\n".join(outputs)
    tool_response = AIMessage(content=combined)

    # Return control back to the chat node so the LLM can continue the dialog
    return Command(goto="chat_node", update={"messages": tool_response})


def create_agent_graph():
    """Builds and compiles the LangGraph StateGraph for the agent."""
    graph = StateGraph(AgentState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tool_node", tool_node)
    graph.set_entry_point("chat_node")

    # compile with an in-memory saver (suitable for local dev). CopilotKit can
    # customize the runnable config later when mounting the agent.
    runnable = graph.compile(MemorySaver())
    return runnable
