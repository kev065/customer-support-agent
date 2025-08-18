"""Terminal REPL to test LangChain/LangGraph tools (Postgres + Qdrant) with LangSmith tracing.

Usage:
  1. Fill in `agent/.env` with OPENAI_API_KEY and LANGCHAIN_API_KEY (LangSmith).
  2. From repo root, start a shell with the env loaded:
       set -a; source ./agent/.env; set +a
  3. Run this script:
       python3 agent/terminal_agent_test.py

This script:
 - Loads environment from agent/.env (via python-dotenv)
 - Ensures LANGCHAIN_TRACING_V2 is enabled so traces go to LangSmith
 - Imports your `all_tools` from `agent.tools` (qdrant retriever tool + order lookup)
 - Binds the tools to an LLM (ChatOpenAI) and runs a small REPL where you can type
   queries like:
     - "What products are good for hiking?"
     - "Show order 12345"

It will print model responses and any tool outputs. Traces will be emitted to LangSmith when LANGCHAIN_API_KEY is set.
"""

import os
import sys
import logging
from typing import Any, Dict

from dotenv import load_dotenv

# Load .env from agent/ directory
HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

# Ensure tracing env vars are set for this process (LangChain v2 tracing)
if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("1", "true", "yes"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

# Ensure project name for LangSmith if set in .env
langchain_project = os.getenv("LANGCHAIN_PROJECT")
if langchain_project:
    os.environ.setdefault("LANGCHAIN_PROJECT", langchain_project)

# Basic logging to help debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import settings so your agent config is respected
from agent.config import settings

# Import the tools you already defined
try:
    from agent.tools import all_tools
except Exception as e:
    logger.error("Failed to import tools from agent.tools: %s", e)
    raise

# Import LangChain/OpenAI model
try:
    # Use the langchain-openai package import which is recommended
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
except Exception:
    # Fall back to older import if not available
    try:
        from langchain.chat_models import ChatOpenAI  # type: ignore
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    except Exception as exc:
        logger.exception("Please install langchain-openai or langchain-community chat model package: %s", exc)
        raise


def get_llm():
    """Create the LLM instance used for the REPL."""
    api_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is not set. Fill it in agent/.env and re-run.")
        sys.exit(1)

    # Use a broadly available model for smoke tests
    return ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo", temperature=0)


def find_tool_by_name(name: str):
    for t in all_tools:
        if getattr(t, "name", None) == name:
            return t
        # Some tools are functions decorated with @tool; `__name__` may be used
        if getattr(t, "__name__", None) == name:
            return t
    return None


def run_tool(tool: Any, arg: Any):
    """Run a tool synchronously (prefers .run, falls back to calling)."""
    try:
        if hasattr(tool, "run"):
            # langchain Tool objects expose .run
            return tool.run(arg)
        # fallback: call the object
        return tool(arg)
    except Exception as e:
        logger.exception("Error running tool %s with arg=%s: %s", getattr(tool, "name", str(tool)), arg, e)
        return f"(tool error) {e}"


def main():
    llm = get_llm()

    # Bind the tools so the model can emit tool calls
    try:
        model_with_tools = llm.bind_tools(all_tools)
    except Exception:
        # If bind_tools isn't available, we'll still call the LLM and then run tools manually
        model_with_tools = llm

    system_message = SystemMessage(content="You are a helpful customer support assistant. Use tools when needed: product_semantic_search and get_order_details.")

    print("Terminal LangChain REPL (type 'exit' to quit)")
    print("Examples: 'What products are good for hiking?', 'Get order 1234'\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        # Build messages for the LLM
        human = HumanMessage(content=user_input)
        try:
            # Try a synchronous invoke first
            response = model_with_tools.invoke([system_message, human])
        except Exception as e:
            logger.warning("Model invoke raised an error; falling back to direct call: %s", e)
            try:
                response = model_with_tools([system_message, human])
            except Exception as e2:
                logger.exception("LLM call failed: %s", e2)
                print("LLM call failed; see logs.")
                continue

        # Print the assistant content if present
        content = getattr(response, "content", None) or str(response)
        print("\n[Assistant]\n", content)

        # If the response contains tool_calls, execute them and show outputs
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            print("\n[Detected tool calls]")
            for tc in tool_calls:
                name = tc.get("name")
                args = tc.get("args") or tc.get("input")
                print(f"- Tool: {name}, args: {args}")

                tool = find_tool_by_name(name)
                if not tool:
                    print(f"  -> No tool named {name} registered locally.")
                    continue

                res = run_tool(tool, args)
                print("  -> Tool result:\n", res)

            # Optionally, send tool outputs back to the model for a follow-up
            followup_texts = []
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool = find_tool_by_name(tool_name)
                if not tool:
                    continue
                res = run_tool(tool, tc.get("args") or tc.get("input"))
                followup_texts.append(f"Result of {tool_name}: {res}")

            if followup_texts:
                assistant_msg = AIMessage(content="\n\n".join(followup_texts))
                try:
                    # Ask the model to continue the conversation with tool outputs
                    response2 = model_with_tools.invoke([system_message, human, assistant_msg])
                    print("\n[Assistant after tools]\n", getattr(response2, "content", str(response2)))
                except Exception as e:
                    logger.exception("Failed to invoke model after tool outputs: %s", e)

    print("Goodbye.")


if __name__ == "__main__":
    main()
