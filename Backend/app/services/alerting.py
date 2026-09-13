"""
Threshold-based alert level logic. Pure functions — no DB, no ML,
no network calls. Fully unit-testable today with dummy scores.

Thresholds are placeholders; tune once you have real score
distributions from the trained model / historical events.
"""

THRESHOLDS = {
    "watch": 0.4,
    "warning": 0.65,
    "severe": 0.85,
}


def get_alert_level(risk_score: float) -> str:
    if risk_score >= THRESHOLDS["severe"]:
        return "severe"
    if risk_score >= THRESHOLDS["warning"]:
        return "warning"
    if risk_score >= THRESHOLDS["watch"]:
        return "watch"
    return "normal"


def get_alert_message(village_name: str, risk_level: str) -> str:
    messages = {
        "normal": f"{village_name}: conditions normal, no action needed.",
        "watch": f"{village_name}: elevated risk detected — monitor conditions closely.",
        "warning": f"{village_name}: high flash flood/landslide risk — prepare for possible evacuation.",
        "severe": f"{village_name}: SEVERE risk — evacuate low-lying/slope-adjacent areas immediately.",
    }
    return messages.get(risk_level, messages["normal"])


if __name__ == "__main__":
    # quick manual sanity check — run: python -m app.services.alerting
    for score in [0.1, 0.45, 0.7, 0.9]:
        level = get_alert_level(score)
        print(score, "->", level, "->", get_alert_message("Test Village", level))
