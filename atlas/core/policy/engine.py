"""
Atlas Sanctum — Policy Engine
Evaluates declarative policies against an execution context.
Policies are registered as Python callables or loaded from YAML rules.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger("atlas.core.policy")

PolicyFn = Callable[[dict[str, Any]], bool]


@dataclass
class PolicyResult:
    allowed: bool
    policy_name: str
    reason: str = ""


class PolicyEngine:
    def __init__(self):
        self._policies: dict[str, PolicyFn] = {}

    def register(self, name: str, fn: PolicyFn) -> None:
        self._policies[name] = fn
        log.debug("Policy registered: %s", name)

    def evaluate(self, name: str, context: dict[str, Any]) -> PolicyResult:
        fn = self._policies.get(name)
        if fn is None:
            return PolicyResult(allowed=False, policy_name=name, reason="policy not found")
        try:
            allowed = fn(context)
            return PolicyResult(allowed=allowed, policy_name=name,
                                reason="ok" if allowed else "policy denied")
        except Exception as exc:
            log.warning("Policy '%s' raised: %s", name, exc)
            return PolicyResult(allowed=False, policy_name=name, reason=str(exc))

    def evaluate_all(self, context: dict[str, Any]) -> list[PolicyResult]:
        return [self.evaluate(name, context) for name in self._policies]


# ---------------------------------------------------------------------------
# Built-in policies
# ---------------------------------------------------------------------------

def human_oversight_required(context: dict[str, Any]) -> bool:
    """High-impact actions require a human_approved flag."""
    if context.get("impact_level", "low") in ("high", "critical"):
        return bool(context.get("human_approved", False))
    return True


def data_minimization(context: dict[str, Any]) -> bool:
    """Reject requests that include PII fields not explicitly consented."""
    pii_fields = {"name", "phone", "email", "address", "national_id"}
    requested = set(context.get("fields", []))
    consented = set(context.get("consented_fields", []))
    return not bool((requested & pii_fields) - consented)
