"""
Demo entrypoint: runs a task through the Aegis Agent DAG and prints
the full execution history, including guardrail checks.
"""
from src.core.graph import build_graph


def main():
    task = "Build a customer support ticket summarizer"
    thread_id = "demo-thread-1"

    graph, conn = build_graph(db_path="aegis_checkpoints.sqlite")
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

    print(f"Running task: {task}")
    print("=" * 60)

    for event in graph.stream(initial_state, config=config):
        for node_name, node_output in event.items():
            print(f"[{node_name}] -> {node_output}")

    final_snapshot = graph.get_state(config)
    print("=" * 60)
    print("Final status:", final_snapshot.values.get("status"))
    print("Full history:")
    for line in final_snapshot.values.get("history", []):
        print(" -", line)

    conn.close()


if __name__ == "__main__":
    main()