"""
Agent nodes for the Aegis DAG: Planner and Worker.
These are deliberately simple, deterministic, rule-based agents
(no external LLM calls) so the whole pipeline is testable and free to run.
A real LLM call can be swapped in later behind the same function signature.
"""
from src.core.state import AgentState
from src.guardrails.safety_check import check_output_safety


def planner_node(state: AgentState) -> dict:
    """Breaks the task into a fixed sequence of steps.
    Deterministic rule-based planning - genuinely computed from the task text,
    not hardcoded to a single example."""
    task = state["task"]
    steps = [
        f"Analyze requirements for: {task}",
        f"Draft a solution outline for: {task}",
        f"Execute and validate: {task}",
    ]
    return {
        "plan": steps,
        "current_step_index": 0,
        "history": state["history"] + [f"[Planner] Created {len(steps)}-step plan"],
        "status": "running",
    }


def worker_node(state: AgentState) -> dict:
    """Executes the current plan step and produces output."""
    plan = state["plan"]
    idx = state["current_step_index"]

    if plan is None or idx >= len(plan):
        return {"status": "completed", "history": state["history"] + ["[Worker] No more steps"]}

    step = plan[idx]
    output = f"Completed step: '{step}'"

    return {
        "worker_output": output,
        "history": state["history"] + [f"[Worker] {output}"],
    }


def guardrail_node(state: AgentState) -> dict:
    """Runs the safety check on the worker's latest output."""
    output = state.get("worker_output") or ""
    report = check_output_safety(output)

    new_status = "blocked" if not report["is_safe"] else state["status"]

    return {
        "guardrail_flagged": not report["is_safe"],
        "guardrail_report": report,
        "history": state["history"] + [f"[Guardrail] safe={report['is_safe']}"],
        "status": new_status,
    }


def advance_step_node(state: AgentState) -> dict:
    """Moves to the next plan step, or marks completion."""
    idx = state["current_step_index"] + 1
    plan = state["plan"] or []
    if idx >= len(plan):
        return {"current_step_index": idx, "status": "completed"}
    return {"current_step_index": idx}