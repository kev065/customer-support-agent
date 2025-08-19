from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from agent.llm import create_agent_graph
from agent.llm import get_llm
from agent.tools import all_tools
from fastapi import HTTPException
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import uuid
import re
import logging
from typing import Any, Dict, List, Optional


app = FastAPI()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # The address of your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create the LangGraph agent graph
agent_graph = create_agent_graph()

# Initialize a CopilotKit remote endpoint and register the LangGraph agent
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="customer_support_agent",
            description="Hyper-aware customer support agent backed by Postgres and Qdrant",
            graph=agent_graph,
        )
    ]
)

# Mount the CopilotKit endpoint at /copilotkit
add_fastapi_endpoint(app, sdk, "/copilotkit", use_thread_pool=False)


@app.get("/health")
def health():
    return {"status": "ok"}


# Simple in-memory session store for demo purposes. Replace with Redis/db in prod.
SESSIONS: Dict[str, Dict[str, Any]] = {}


class CreateSessionResponse(BaseModel):
    session_id: str


class MessageRequest(BaseModel):
    text: str


class MessageResponse(BaseModel):
    assistant: str
    tool_outputs: Optional[List[Dict[str, Any]]] = None


def find_tool_by_name(name: str):
    for t in all_tools:
        if getattr(t, "name", None) == name:
            return t
        if getattr(t, "__name__", None) == name:
            return t
    return None


def run_tool(tool: Any, arg: Any):
    try:
        if hasattr(tool, "run"):
            return tool.run(arg)
        return tool(arg)
    except Exception as e:
        logging.exception("Error running tool %s: %s", getattr(tool, "name", str(tool)), e)
        return f"(tool error) {e}"


def pretty_format_tool_result(result: Any) -> str:
    try:
        import json

        if isinstance(result, list) and result and all(hasattr(r, "page_content") for r in result):
            parts = []
            for i, doc in enumerate(result[:10], 1):
                meta = getattr(doc, "metadata", {}) or {}
                content = getattr(doc, 'page_content', '') or ''
                if not content.strip():
                    candidates = []
                    for k in ("description", "text", "content", "name"):
                        v = meta.get(k)
                        if v:
                            candidates.append(str(v))
                    if not candidates and isinstance(meta.get('payload'), dict):
                        payload = meta.get('payload')
                        for k in ("description", "text", "name"):
                            v = payload.get(k)
                            if v:
                                candidates.append(str(v))
                    content = candidates[0] if candidates else ''

                meta_summary = {}
                for key in ("name", "id", "score"):
                    if key in meta:
                        meta_summary[key] = meta[key]

                meta_json = json.dumps(meta_summary) if meta_summary else json.dumps(meta)
                parts.append(f"[{i}] {content}\n  metadata: {meta_json}")
            if len(result) > 10:
                parts.append(f"...and {len(result)-10} more documents")
            return "\n\n".join(parts)

        if isinstance(result, list) and all(isinstance(r, dict) for r in result):
            return "\n\n".join(json.dumps(r, default=str, indent=2) for r in result)

        if isinstance(result, dict):
            return json.dumps(result, default=str, indent=2)
    except Exception:
        pass
    try:
        return str(result)
    except Exception:
        return repr(result)


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session() -> CreateSessionResponse:
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {"last_order_id": None}
    return CreateSessionResponse(session_id=sid)


@app.post("/sessions/{session_id}/message", response_model=MessageResponse)
def post_message(session_id: str, req: MessageRequest) -> MessageResponse:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    mem_hint = ""
    if session.get("last_order_id"):
        mem_hint = (
            f"\nSession memory: the user previously provided order id={session['last_order_id']}. "
            "If the user asks about that order, you may use this id without asking again."
        )

    system_message = SystemMessage(content=(
        "You are a helpful customer support assistant. Use tools when needed: product_semantic_search and get_order_details. "
        "When replying to the user, always start with a concise, natural-language answer (one or two sentences). "
        "If you include structured data, put a short natural-language summary first, then include the data as JSON only when explicitly asked. "
        "Be brief and user-facing — do not return raw Python objects or plain JSON unless the user asks for it."
        + mem_hint
    ))

    human = HumanMessage(content=req.text)

    model = get_llm()
    copilot_actions = []
    tools = [*all_tools, *copilot_actions]
    try:
        model_with_tools = model.bind_tools(tools)
    except Exception:
        model_with_tools = model

    try:
        response = model_with_tools.invoke([system_message, human])
    except Exception as e:
        logging.exception("LLM invoke failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    content = getattr(response, "content", "")
    tool_calls = getattr(response, "tool_calls", None) or []
    tool_outputs_for_model = []

    if tool_calls:
        for tc in tool_calls:
            name = tc.get("name")
            args = tc.get("args") or tc.get("input")
            if not args and name == "get_order_details" and session.get("last_order_id"):
                args = {"order_id": session["last_order_id"]}

            tool = find_tool_by_name(name)
            if not tool:
                tool_outputs_for_model.append({"tool": name, "output": "(no local tool)"})
                continue

            raw = run_tool(tool, args)
            pretty = pretty_format_tool_result(raw)
            tool_outputs_for_model.append({"tool": name, "output": pretty})

            if name == "get_order_details":
                m = re.search(r"Order ID:\s*(\d+)", pretty)
                if m:
                    session["last_order_id"] = int(m.group(1))

        followup_texts = []
        for t in tool_outputs_for_model:
            followup_texts.append(f"TOOL_OUTPUT {t['tool']}:\n{t['output']}")

        assistant_msg = AIMessage(content="\n\n".join(followup_texts))

        # Ask the model explicitly to produce a concise, user-facing reply
        followup_instruction = HumanMessage(content=(
            "Using the TOOL_OUTPUTS above, produce a concise natural-language reply to the user. "
            "Start with a one-line summary, then optionally add one short paragraph of details. "
            "Do NOT return raw JSON unless the user asked for it."
        ))

        try:
            response2 = model_with_tools.invoke([system_message, human, assistant_msg, followup_instruction])
            final = getattr(response2, "content", "")
        except Exception as e:
            logging.exception("LLM follow-up failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

        # If the model didn't return a friendly reply for any reason, craft a small fallback
        if not final or not str(final).strip():
            # Try to craft a reply from known tool outputs (e.g., get_order_details)
            fallback = None
            for t in tool_outputs_for_model:
                if t["tool"] == "get_order_details":
                    out = t["output"]
                    m_id = re.search(r"Order ID:\s*(\d+)", out)
                    m_status = re.search(r"Status:\s*([A-Za-z0-9 _-]+)", out)
                    m_date = re.search(r"Date:\s*([0-9-]+)", out)
                    m_total = re.search(r"Total Amount:\s*\$?([0-9.,]+)", out)
                    if m_id and m_status:
                        oid = m_id.group(1)
                        status = m_status.group(1).strip()
                        date = m_date.group(1) if m_date else None
                        total = m_total.group(1) if m_total else None
                        parts = [f"Your order {oid} is currently {status}."]
                        if date:
                            parts.append(f"It was placed on {date}.")
                        if total:
                            parts.append(f"The total amount was ${total}.")
                        fallback = " ".join(parts)
                        break

            final = fallback or "I retrieved some information but couldn't summarize it. Please ask for more details."

        return MessageResponse(assistant=final, tool_outputs=tool_outputs_for_model)

    return MessageResponse(assistant=content, tool_outputs=None)
