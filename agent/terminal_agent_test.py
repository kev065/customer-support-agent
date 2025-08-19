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
import json
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


def pretty_format_tool_result(result: Any) -> str:
    """Convert various tool result types into a human-friendly string.

    Handles:
      - langchain Document lists (has page_content)
      - lists of dicts (e.g., DB rows)
      - single dicts
      - other objects (fall back to str)
    """
    # Documents from LangChain
    try:
        if isinstance(result, list) and result:
            first = result[0]
            # LangChain Document-like objects
            if hasattr(first, "page_content"):
                parts = []
                for i, doc in enumerate(result[:10], 1):
                    meta = getattr(doc, "metadata", {}) or {}
                    content = getattr(doc, 'page_content', '') or ''
                    # If page_content is empty, try to build a short summary from metadata
                    if not content or not content.strip():
                        # common metadata keys that may contain useful text
                        candidates = []
                        for k in ("description", "text", "content", "name"):
                            v = meta.get(k)
                            if v:
                                candidates.append(str(v))
                        # also some Qdrant payloads are nested under 'payload' key
                        if not candidates and isinstance(meta.get('payload'), dict):
                            payload = meta.get('payload')
                            for k in ("description", "text", "name"):
                                v = payload.get(k)
                                if v:
                                    candidates.append(str(v))

                        content = candidates[0] if candidates else ''

                    # Build a readable line including metadata highlights
                    meta_summary = {}
                    for key in ("name", "id", "score"):
                        if key in meta:
                            meta_summary[key] = meta[key]

                    meta_json = json.dumps(meta_summary) if meta_summary else json.dumps(meta)
                    parts.append(f"[{i}] {content}\n  metadata: {meta_json}")
                if len(result) > 10:
                    parts.append(f"...and {len(result)-10} more documents")
                return "\n\n".join(parts)

        # List of dict-like rows (e.g., DB results)
        if isinstance(result, list) and all(isinstance(r, dict) for r in result):
            return "\n\n".join(json.dumps(r, default=str, indent=2) for r in result)

        if isinstance(result, dict):
            return json.dumps(result, default=str, indent=2)

    except Exception:
        # Fall back to str()
        pass

    # Default
    try:
        return str(result)
    except Exception:
        return repr(result)


def main():
    llm = get_llm()

    # Bind the tools so the model can emit tool calls
    try:
        model_with_tools = llm.bind_tools(all_tools)
    except Exception:
        # If bind_tools isn't available, we'll still call the LLM and then run tools manually
        model_with_tools = llm

    # Session memory stored locally in the REPL (short-lived per process run)
    session_state: dict = {}

    # We'll build the system instruction per-turn so we can surface any short-term
    # memory (for example: last_order_id) to the model. This helps the model avoid
    # asking for the order id again on follow-up turns.

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

        # Build messages for the LLM. Include session memory in the system prompt.
        mem_hint = ""
        if session_state.get("last_order_id"):
            mem_hint = (
                f"\nSession memory: the user previously provided order id={session_state['last_order_id']}. "
                "If the user asks about that order, you may use this id without asking again."
            )

        system_message = SystemMessage(content=(
            "You are a helpful customer support assistant. Use tools when needed: product_semantic_search and get_order_details. "
            "When replying to the user, always start with a concise, natural-language answer (one or two sentences). "
            "If you include structured data, put a short natural-language summary first, then include the data as JSON only when explicitly asked. "
            "Be brief and user-facing — do not return raw Python objects or plain JSON unless the user asks for it."
            + mem_hint
        ))

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

            # Run each tool once, collect pretty outputs and raw outputs for the model
            tool_outputs_for_model = []
            for tc in tool_calls:
                name = tc.get("name")
                args = tc.get("args") or tc.get("input")
                # If the model called get_order_details without args, use session memory
                # to fill the missing order id when available.
                if not args and name == "get_order_details" and session_state.get("last_order_id"):
                    args = {"order_id": session_state["last_order_id"]}
                    print(f"  -> Using remembered order_id={session_state['last_order_id']} for tool {name}")
                print(f"- Tool: {name}, args: {args}")

                tool = find_tool_by_name(name)
                if not tool:
                    print(f"  -> No tool named {name} registered locally.")
                    tool_outputs_for_model.append((name, f"(no local tool)"))
                    continue

                raw_res = run_tool(tool, args)
                pretty = pretty_format_tool_result(raw_res)
                print("  -> Tool result:\n", pretty)
                tool_outputs_for_model.append((name, pretty))

                # Try to detect order id in the tool result so we can remember it for
                # follow-up turns. We look for a line like 'Order ID: 1234'.
                try:
                    if name == "get_order_details":
                        import re

                        m = re.search(r"Order ID:\s*(\d+)", pretty)
                        if m:
                            session_state["last_order_id"] = int(m.group(1))
                except Exception:
                    # non-fatal; if parsing fails we just don't update memory
                    pass

            # Send tool outputs back to the model in a single assistant message.
            # We wrap outputs clearly so the model knows these are tool results and
            # must produce a natural-language reply for the user.
            followup_parts = []
            for name, pretty in tool_outputs_for_model:
                followup_parts.append(f"TOOL_OUTPUT {name}:")
                followup_parts.append(pretty)

            if followup_parts:
                assistant_msg = AIMessage(content="\n\n".join(followup_parts))
                try:
                    # Ask the model to continue the conversation with tool outputs
                    response2 = model_with_tools.invoke([system_message, human, assistant_msg])
                    final = getattr(response2, "content", str(response2))
                    print("\n[Assistant after tools]\n", final)
                except Exception as e:
                    logger.exception("Failed to invoke model after tool outputs: %s", e)

    print("Goodbye.")


if __name__ == "__main__":
    main()