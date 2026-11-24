"""Small, deterministic policy evaluator. Default effect is deny; explicit deny overrides allow."""
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def evaluate_policy(
    db: Session,
    *,
    subject: str,
    action: str,
    resource: str,
    facts: dict[str, Any],
) -> bool:
    rules = db.execute(text("""
        SELECT pr.effect, pr.conditions
        FROM policy_rules pr
        JOIN policy_packs pp ON pp.id = pr.policy_pack_id
        WHERE pp.status = 'active'
          AND pr.subject IN (:subject, '*')
          AND pr.action = :action
          AND pr.resource = :resource
    """), {"subject": subject, "action": action, "resource": resource}).mappings().all()

    matching_effects: list[str] = []
    for rule in rules:
        conditions = rule["conditions"]
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        if not isinstance(conditions, dict):
            continue
        if all(facts.get(key) == expected for key, expected in conditions.items()):
            matching_effects.append(rule["effect"])

    if "deny" in matching_effects:
        return False
    return "allow" in matching_effects
