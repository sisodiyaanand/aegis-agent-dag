"""
Genuine state-recovery test: verifies that SQLite checkpointing actually
persists state across separate graph invocations (simulating a crash and
restart), rather than restarting the task from scratch.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.core.graph import build_graph

TEST_DB = "test_recovery_checkpoints.sqlite"


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_state_persists_across_separate_graph_instances():
    """
    Simulates a crash: we build the graph, run it, close the connection
    (as if the process died), then build a BRAND NEW graph instance
    pointing at the same DB and thread_id, and verify the checkpointed
    state is still there - proving recovery is real, not simulated.
    """
    _cleanup()
    thread_id = "recovery-test-thread"

    # --- "Run 1": start the task and let it complete ---
    graph1, conn1 = build_graph(db_path=TEST_DB)
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "task": "Test recovery task",
        "plan": None,
        "current_step_index": 0,
        "worker_output": None,
        "history": [],
        "guardrail_flagged": False,
        "guardrail_report": None,
        "status": "running",
    }
    for _ in graph1.stream(initial_state, config=config):
        pass

    snapshot_before = graph1.get_state(config)
    history_before = snapshot_before.values["history"]
    assert len(history_before) > 0

    # Simulate a crash: close the connection, delete the in-memory graph object
    conn1.close()
    del graph1

    # --- "Run 2": brand-new process would do this ---
    graph2, conn2 = build_graph(db_path=TEST_DB)
    snapshot_after = graph2.get_state(config)

    # The history from Run 1 must still be readable from a fresh graph instance
    history_after = snapshot_after.values["history"]
    assert history_after == history_before
    assert snapshot_after.values["status"] == "completed"

    conn2.close()
    _cleanup()


def test_different_thread_ids_have_independent_state():
    """Two different thread_ids must not share or overwrite each other's state."""
    _cleanup()
    graph, conn = build_graph(db_path=TEST_DB)

    for thread_id, task in [("thread-A", "Task A"), ("thread-B", "Task B")]:
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "task": task,
            "plan": None,
            "current_step_index": 0,
            "worker_output": None,
            "history": [],
            "guardrail_flagged": False,
            "guardrail_report": None,
            "status": "running",
        }
        for _ in graph.stream(initial_state, config=config):
            pass

    state_a = graph.get_state({"configurable": {"thread_id": "thread-A"}})
    state_b = graph.get_state({"configurable": {"thread_id": "thread-B"}})

    assert state_a.values["task"] == "Task A"
    assert state_b.values["task"] == "Task B"
    assert state_a.values["history"] != state_b.values["history"]

    conn.close()
    _cleanup()