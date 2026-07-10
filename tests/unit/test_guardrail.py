"""
Tests for the guardrail safety check and its ability to halt the DAG
when unsafe output is detected.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.guardrails.safety_check import check_output_safety
from src.agents.nodes import guardrail_node


def test_safe_output_passes():
    result = check_output_safety("Completed step: analyze customer requirements")
    assert result["is_safe"] is True
    assert result["flagged_terms"] == []


def test_unsafe_output_is_flagged():
    result = check_output_safety("Let's hack the admin panel and bypass security")
    assert result["is_safe"] is False
    assert len(result["flagged_terms"]) > 0


def test_empty_output_is_safe():
    result = check_output_safety("")
    assert result["is_safe"] is True
    assert result["risk_score"] == 0.0


def test_guardrail_node_blocks_status_on_unsafe_output():
    state = {
        "task": "test",
        "plan": ["step1"],
        "current_step_index": 0,
        "worker_output": "drop table users; rm -rf /",
        "history": [],
        "guardrail_flagged": False,
        "guardrail_report": None,
        "status": "running",
    }
    result = guardrail_node(state)
    assert result["guardrail_flagged"] is True
    assert result["status"] == "blocked"


def test_guardrail_node_allows_safe_output():
    state = {
        "task": "test",
        "plan": ["step1"],
        "current_step_index": 0,
        "worker_output": "Completed step successfully",
        "history": [],
        "guardrail_flagged": False,
        "guardrail_report": None,
        "status": "running",
    }
    result = guardrail_node(state)
    assert result["guardrail_flagged"] is False
    assert result["status"] == "running"