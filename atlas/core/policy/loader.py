"""
Atlas Sanctum — Policy Rule Loader
Loads declarative YAML rules and registers them with the PolicyEngine.

Rule format (rules.yaml):
  - name: human_oversight
    description: High-impact actions need human approval
    condition: "context.get('impact_level','low') not in ('high','critical') or context.get('human_approved', False)"
    effect: allow
    priority: 10
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from atlas.core.policy.engine import PolicyEngine, PolicyResult
from atlas.schemas.phase2 import PolicyRule

log = logging.getLogger("atlas.core.policy.loader")

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def load_rules_from_yaml(path: Path) -> list[PolicyRule]:
    if not _YAML_AVAILABLE:
        raise RuntimeError("PyYAML is required for YAML rule loading: pip install pyyaml")
    data = yaml.safe_load(path.read_text()) or []
    return [PolicyRule(**r) for r in data]


def register_yaml_rules(engine: PolicyEngine, path: Path) -> int:
    rules = load_rules_from_yaml(path)
    for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
        _register_rule(engine, rule)
    log.info("Loaded %d policy rules from %s", len(rules), path)
    return len(rules)


def _register_rule(engine: PolicyEngine, rule: PolicyRule) -> None:
    condition = rule.condition
    effect = rule.effect

    def _fn(context: dict[str, Any]) -> bool:
        result = bool(eval(condition, {"context": context}))  # noqa: S307
        return result if effect == "allow" else not result

    engine.register(rule.name, _fn)
