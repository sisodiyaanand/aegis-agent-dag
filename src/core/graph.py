"""
Builds the Aegis Agent DAG using LangGraph, with SQLite-backed checkpointing
for real state persistence and crash recovery.
"""
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.core.state import AgentState
from src.agents.nodes import planner_node, worker_node, guardrail_node, advance_step_node


def route_after_guardrail(state: AgentState) -> str:
    """Decides where to go after the guardrail check:
    - if blocked -> END (unsafe output stops the pipeline)
    - if plan finished -> END
    - otherwise -> advance to next step and loop back to worker
    """
    if state["status"] == "blocked":
        return "end"
    if state["status"] == "completed":
        return "end"
    return "continue"


def build_graph(db_path: str = "aegis_checkpoints.sqlite"):
    """Compiles the graph with a real SQLite checkpointer.
    Returns (graph, checkpointer) - caller is responsible for closing
    the underlying sqlite connection when done."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("worker", worker_node)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("advance", advance_step_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "worker")
    builder.add_edge("worker", "guardrail")

    builder.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"continue": "advance", "end": END},
    )
    builder.add_edge("advance", "worker")

    graph = builder.compile(checkpointer=checkpointer)
    return graph, conn


def run_task(task: str, thread_id: str = "default-thread", db_path: str = "aegis_checkpoints.sqlite"):
    """Runs a task through the full DAG, using thread_id to identify
    the checkpointed session (so it can be resumed later)."""
    graph, conn = build_graph(db_path)
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "task": task,
        "plan": None,
        "current_step_index": 0,
        "worker_output": None,
        "history": [],
        "guardrail_flagged": False,
        "guardrail_report": None,
        "status": "running",
    }

    final_state = None
    for event in graph.stream(initial_state, config=config):
        final_state = event

    conn.close()
    return final_state