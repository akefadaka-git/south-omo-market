"""Deterministic policy evaluator. Default effect is deny; explicit deny overrides allow."""
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
    """Evaluate active rules with exact-or-wildcard matching and fail-closed conditions."""
    rules = db.execute(text("""
        SELECT pr.effect, pr.conditions
        FROM policy_rules pr
        JOIN policy_packs pp ON pp.id = pr.policy_pack_id
        WHERE pp.status = 'active'
          AND pr.subject IN (:subject, '*')
          AND pr.action IN (:action, '*')
          AND pr.resource IN (:resource, '*')
    """), {"subject": subject, "action": action, "resource": resource}).mappings().all()

    matching_effects: list[str] = []
    for rule in rules:
        conditions = rule["conditions"]
        try:
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
        except (TypeError, ValueError):
            return False
        if not isinstance(conditions, dict):
            return False
        if not all(key in facts and facts[key] == expected for key, expected in conditions.items()):
            continue
        effect = rule["effect"]
        if effect not in {"allow", "deny"}:
            return False
        matching_effects.append(effect)

    if "deny" in matching_effects:
        return False
    return "allow" in matching_effects
