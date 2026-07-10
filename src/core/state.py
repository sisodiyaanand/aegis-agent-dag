"""
Shared state schema for the Aegis Agent DAG.
This TypedDict is passed between every node in the graph and is what
gets checkpointed to SQLite after each step.
"""
from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    task: str                      # original user task
    plan: Optional[List[str]]      # steps produced by the planner
    current_step_index: int        # which plan step we're executing
    worker_output: Optional[str]   # latest worker output
    history: List[str]             # log of all steps taken so far
    guardrail_flagged: bool        # did the last output fail a safety check?
    guardrail_report: Optional[dict]
    status: str                    # "running" | "completed" | "blocked"