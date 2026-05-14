from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertRule:
    metric_type: str
    operator: str
    threshold: float
    alert_type: str
    severity: str
    message: str


ALERT_RULES: dict[str, list[AlertRule]] = {
    "heart_rate": [
        AlertRule("heart_rate", ">", 120, "HIGH_HEART_RATE", "high", "Heart rate is above 120 bpm"),
        AlertRule("heart_rate", "<", 40, "LOW_HEART_RATE", "high", "Heart rate is below 40 bpm"),
    ],
    "spo2": [
        AlertRule("spo2", "<", 90, "LOW_OXYGEN", "critical", "SpO2 is below 90%"),
    ],
    "body_temperature": [
        AlertRule("body_temperature", ">", 38, "FEVER", "medium", "Body temperature is above 38 C"),
    ],
}


def evaluate_alert_rules(metric_type: str, value: float) -> list[AlertRule]:
    rules = ALERT_RULES.get(metric_type, [])
    matched: list[AlertRule] = []
    for rule in rules:
        if rule.operator == ">" and value > rule.threshold:
            matched.append(rule)
        elif rule.operator == "<" and value < rule.threshold:
            matched.append(rule)
    return matched
