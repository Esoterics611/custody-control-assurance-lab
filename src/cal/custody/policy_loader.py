"""Build a :class:`PolicyEngine` from a declarative YAML policy file."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml

from cal.custody.policy_engine import PolicyEngine, PolicyRule
from cal.models import Decision, DestinationType, TransactionType

# Repo-root-relative default policy.
DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "default_policy.yaml"


def _enum_tuple(values, enum_cls):
    if values is None:
        return None
    return tuple(enum_cls(v) for v in values)


def _str_tuple(values):
    if values is None:
        return None
    return tuple(str(v) for v in values)


def _decimal_or_none(value):
    return None if value is None else Decimal(str(value))


def rule_from_dict(raw: dict) -> PolicyRule:
    return PolicyRule(
        name=raw["name"],
        action=Decision(raw["action"]),
        initiator_groups=_str_tuple(raw.get("initiator_groups")),
        source_vaults=_str_tuple(raw.get("source_vaults")),
        destination_types=_enum_tuple(raw.get("destination_types"), DestinationType),
        assets=_str_tuple(raw.get("assets")),
        tx_types=_enum_tuple(raw.get("tx_types"), TransactionType),
        min_amount_usd=_decimal_or_none(raw.get("min_amount_usd")),
        period_sec=raw.get("period_sec"),
        window_limit_usd=_decimal_or_none(raw.get("window_limit_usd")),
        required_approvals=int(raw.get("required_approvals", 0)),
        approver_group=raw.get("approver_group"),
    )


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> PolicyEngine:
    data = yaml.safe_load(Path(path).read_text())
    groups = {name: tuple(members) for name, members in (data.get("groups") or {}).items()}
    rules = [rule_from_dict(r) for r in data.get("rules", [])]
    return PolicyEngine(rules=rules, group_membership=groups)
