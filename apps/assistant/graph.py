"""The assistant as a LangGraph: an agent node that can call two read-only tools, looping until it can answer.

        START -> agent --(wants a tool)--> tools -> agent ... --(answer ready)--> END

The tools close over one client's scope, so a graph is built per request; conversation memory is kept per thread."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from . import db
from .guard import UnsafeSQL
from .prompt import parts

MEMORY = MemorySaver()
MODEL_ROWS = 40       # rows the model sees per query (the user sees more in the trace)
CELL_CHARS = 150


def providers() -> list[str]:
    """The models that have a key, the preferred one (ASSISTANT_PROVIDER) first; the other follows when fallback is on."""
    keys = {"anthropic": settings.ANTHROPIC_API_KEY, "gemini": settings.GEMINI_API_KEY}
    first = settings.ASSISTANT_PROVIDER if settings.ASSISTANT_PROVIDER in keys else "anthropic"
    order = [first] + ([p for p in keys if p != first] if settings.ASSISTANT_FALLBACK else [])
    return [p for p in order if keys[p]]


def make_llm(provider: str | None = None):
    provider = provider or (providers() or ["anthropic"])[0]
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=settings.ASSISTANT_GEMINI_MODEL, google_api_key=settings.GEMINI_API_KEY, temperature=0,
                                      max_output_tokens=settings.ASSISTANT_GEMINI_MAX_TOKENS, timeout=90)
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=settings.ASSISTANT_MODEL, api_key=settings.ANTHROPIC_API_KEY, temperature=0,
                         max_tokens=1500, timeout=90)


def _tools(client_id, trace: list, outlet_ids=None):
    @tool
    def describe_schema() -> str:
        """List the read-only views and their columns you can query with run_sql."""
        return json.dumps(db.describe())

    @tool
    def run_sql(sql: str) -> str:
        """Run ONE PostgreSQL SELECT on the views from describe_schema. Returns JSON {columns, rows, truncated}. Read-only."""
        entry = {"sql": sql}
        trace.append(entry)
        try:
            res = db.run(sql, client_id, outlet_ids)
        except UnsafeSQL as e:
            entry["error"] = str(e)
            return f"Rejected: {e}"
        except Exception as e:  # a database error the model can read and fix
            entry["error"] = str(e).strip().splitlines()[0][:300]
            return f"SQL error: {entry['error']}"
        entry.update(columns=res["columns"], rows=res["rows"][:50], total_rows=len(res["rows"]), truncated=res["truncated"], ms=res["ms"])
        shown = [{k: (v[:CELL_CHARS] if isinstance(v, str) else v) for k, v in r.items()} for r in res["rows"][:MODEL_ROWS]]
        note = ""
        if len(res["rows"]) > MODEL_ROWS or res["truncated"]:
            note = f"Only the first {MODEL_ROWS} rows are shown; aggregate or filter to see the rest."
        return json.dumps({"columns": res["columns"], "rows": shown, "row_count": len(res["rows"]), "note": note}, default=str)

    return [describe_schema, run_sql]


def _system_message(llm, fixed: str, dynamic: str) -> SystemMessage:
    """Claude: the fixed instructions + schema are marked cacheable (re-read at a tenth of the price on the next calls and
    questions within a few minutes); the per-request part comes after it so it never breaks the cache. Others get plain text,
    fixed part first (Gemini caches a repeated prefix by itself)."""
    if type(llm).__name__ == "ChatAnthropic":
        return SystemMessage(content=[{"type": "text", "text": fixed, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": dynamic}])
    return SystemMessage(content=fixed + "\n" + dynamic)


def build_graph(client_id, system_prompt, trace: list, llm=None, outlet_ids=None):
    """system_prompt: (fixed text, per-request text), or one string."""
    tools = _tools(client_id, trace, outlet_ids)
    llm = llm or make_llm()
    model = llm.bind_tools(tools)
    system = _system_message(llm, *system_prompt) if isinstance(system_prompt, tuple) else SystemMessage(content=system_prompt)

    def agent(state: MessagesState):
        history = trim_messages(state["messages"], max_tokens=20, token_counter=len, strategy="last",
                                start_on="human", include_system=False, allow_partial=False)
        return {"messages": [model.invoke([system, *history])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=MEMORY)


class EmptyAnswer(Exception):
    """The model finished without writing any text."""


def ask(message: str, thread_key: str, client_id, who: str, page: str, llm=None, outlet_ids=None, strict: bool = False) -> tuple[str, list]:
    """Run one turn. Returns (answer text, trace of the queries that were run). strict: raise EmptyAnswer instead of returning
    the 'could not produce an answer' text, so the caller can try another model."""
    from langgraph.errors import GraphRecursionError

    trace: list = []
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A %d %B %Y, %H:%M")
    graph = build_graph(client_id, parts(who, page, today, settings.ASSISTANT_MAX_ROWS, db.schema_text()), trace, llm, outlet_ids)
    config = {"configurable": {"thread_id": thread_key}, "recursion_limit": 2 * settings.ASSISTANT_MAX_STEPS + 2}
    try:
        out = graph.invoke({"messages": [("user", message)]}, config)
    except GraphRecursionError:
        return "That question is too broad for me to answer in one go. Try narrowing it, for example to one outlet or one week.", trace
    last = out["messages"][-1]
    text = last.content if isinstance(last.content, str) else "".join(
        b.get("text", "") for b in last.content if isinstance(b, dict) and b.get("type") == "text")
    if not text.strip():
        import logging

        logging.getLogger(__name__).warning("assistant: empty answer (finish_reason=%s, usage=%s)",
                                            (getattr(last, "response_metadata", None) or {}).get("finish_reason"), getattr(last, "usage_metadata", None))
        if strict:
            raise EmptyAnswer("the model wrote no answer")
    return text.strip() or "I could not produce an answer. Please rephrase the question.", trace
