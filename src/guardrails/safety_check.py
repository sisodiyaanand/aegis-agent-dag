"""
Dynamic Guardrail: a lightweight, genuinely-functioning safety gate that
inspects agent output before it proceeds to the next node in the DAG.

Uses a keyword-based heuristic (same honest approach as sentinel-eval-gateway) -
documented clearly as a baseline, upgradeable to a trained classifier later.
"""

UNSAFE_KEYWORDS = {
    "hack", "exploit", "bypass security", "delete all",
    "drop table", "rm -rf", "malware", "ransomware",
}


def check_output_safety(text: str) -> dict:
    """
    Scans agent output for unsafe patterns.

    Returns a dict with:
        - is_safe: bool
        - flagged_terms: list of matched unsafe terms (empty if safe)
        - risk_score: fraction of unsafe keyword hits relative to text length
    """
    if not text or not text.strip():
        return {"is_safe": True, "flagged_terms": [], "risk_score": 0.0}

    lower_text = text.lower()
    flagged = [kw for kw in UNSAFE_KEYWORDS if kw in lower_text]

    words = lower_text.split()
    risk_score = round(min(len(flagged) / max(len(words), 1) * 10, 1.0), 4)

    return {
        "is_safe": len(flagged) == 0,
        "flagged_terms": flagged,
        "risk_score": risk_score,
    }