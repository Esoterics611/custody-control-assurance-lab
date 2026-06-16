"""Pre-signing compliance screening.

Models a sanctions/risk intel lookup (in the spirit of nexus-protocol's
``RestrictionList`` OFAC denylist + a risk score) plus a Travel-Rule flag. All
intel is SYNTHETIC. ``screen`` is pure: ``request -> ScreeningResult``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from cal.models import DestinationType, ScreeningResult, TransactionRequest

# Categories that are an UNCONDITIONAL block, independent of numeric score.
SANCTIONED_CATEGORIES = frozenset({"OFAC_SANCTION", "SANCTIONS", "TERROR_FINANCING"})

# Destination kinds that trigger Travel-Rule data collection above the threshold.
TRAVEL_RULE_DESTINATIONS = frozenset({DestinationType.ONE_TIME, DestinationType.UNMANAGED_CONTRACT})

DEFAULT_SANCTIONS_PATH = Path(__file__).resolve().parents[3] / "data" / "sanctions.sample.json"


@dataclass
class ScreeningEngine:
    intel: dict[str, dict] = field(default_factory=dict)
    risk_ceiling: int = 75
    travel_rule_threshold_usd: Decimal = Decimal("1000")

    @classmethod
    def from_file(
        cls,
        path: Path | str = DEFAULT_SANCTIONS_PATH,
        *,
        risk_ceiling: int = 75,
        travel_rule_threshold_usd: Decimal = Decimal("1000"),
    ) -> ScreeningEngine:
        data = json.loads(Path(path).read_text())
        intel: dict[str, dict] = {}
        for entry in data.get("addresses", []):
            intel[entry["address"].lower()] = {
                "score": int(entry.get("score", 0)),
                "categories": tuple(entry.get("categories", ())),
            }
        return cls(
            intel=intel,
            risk_ceiling=risk_ceiling,
            travel_rule_threshold_usd=travel_rule_threshold_usd,
        )

    def screen(self, request: TransactionRequest) -> ScreeningResult:
        entry = self.intel.get(request.destination.lower())
        categories: tuple[str, ...] = tuple(entry["categories"]) if entry else ()
        score: int = entry["score"] if entry else 0

        travel_rule_required = (
            request.destination_type in TRAVEL_RULE_DESTINATIONS
            and request.amount_usd >= self.travel_rule_threshold_usd
        )

        sanctioned_hits = sorted(set(categories) & SANCTIONED_CATEGORIES)
        if sanctioned_hits:
            return ScreeningResult(
                passed=False,
                score=score,
                categories=categories,
                travel_rule_required=travel_rule_required,
                reason=f"sanctioned destination ({', '.join(sanctioned_hits)})",
            )

        if score >= self.risk_ceiling:
            return ScreeningResult(
                passed=False,
                score=score,
                categories=categories,
                travel_rule_required=travel_rule_required,
                reason=f"risk score {score} >= ceiling {self.risk_ceiling}",
            )

        return ScreeningResult(
            passed=True,
            score=score,
            categories=categories,
            travel_rule_required=travel_rule_required,
            reason="cleared screening",
        )
