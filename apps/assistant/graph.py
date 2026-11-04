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
from .prompt import build

MEMORY = MemorySaver()
MODEL_ROWS = 60       # rows the model sees per query (the user sees more in the trace)
CELL_CHARS = 300


def make_llm():
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=settings.ASSISTANT_MODEL, api_key=settings.ANTHROPIC_API_KEY, temperature=0,
                         max_tokens=2500, timeout=90)


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


def build_graph(client_id, system_prompt: str, trace: list, llm=None, outlet_ids=None):
    tools = _tools(client_id, trace, outlet_ids)
    model = (llm or make_llm()).bind_tools(tools)
    system = SystemMessage(content=system_prompt)

    def agent(state: MessagesState):
        history = trim_messages(state["messages"], max_tokens=30, token_counter=len, strategy="last",
                                start_on="human", include_system=False, allow_partial=False)
        return {"messages": [model.invoke([system, *history])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=MEMORY)


def ask(message: str, thread_key: str, client_id, who: str, page: str, llm=None, outlet_ids=None) -> tuple[str, list]:
    """Run one turn. Returns (answer text, trace of the queries that were run)."""
    from langgraph.errors import GraphRecursionError

    trace: list = []
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A %d %B %Y, %H:%M")
    graph = build_graph(client_id, build(who, page, today, settings.ASSISTANT_MAX_ROWS), trace, llm, outlet_ids)
    config = {"configurable": {"thread_id": thread_key}, "recursion_limit": 2 * settings.ASSISTANT_MAX_STEPS + 2}
    try:
        out = graph.invoke({"messages": [("user", message)]}, config)
    except GraphRecursionError:
        return "That needed more steps than I am allowed to take. Try a narrower question, for example one outlet or one week.", trace
    last = out["messages"][-1]
    text = last.content if isinstance(last.content, str) else "".join(
        b.get("text", "") for b in last.content if isinstance(b, dict) and b.get("type") == "text")
    return text.strip() or "I could not produce an answer. Please rephrase the question.", trace
