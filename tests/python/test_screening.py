"""Unit tests for compliance screening — sanctions, risk boundary, Travel Rule."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cal.custody.screening import ScreeningEngine
from cal.models import DestinationType, TransactionRequest, TransactionType

pytestmark = pytest.mark.unit

T0 = 1_700_000_000.0

# Synthetic addresses present in data/sanctions.sample.json.
ADDR_SANCTIONED = "0xSANCTIONED00000000000000000000000000000001"
ADDR_MIXER = "0xMIXER0000000000000000000000000000000000002"
ADDR_WATCH75 = "0xWATCH75000000000000000000000000000000000005"
ADDR_WATCH74 = "0xWATCH74000000000000000000000000000000000006"
ADDR_UNKNOWN = "0xCLEAN0000000000000000000000000000000000099"


@pytest.fixture
def screening() -> ScreeningEngine:
    return ScreeningEngine.from_file()


def make_request(
    *,
    destination: str,
    amount: str = "5000",
    destination_type: DestinationType = DestinationType.WHITELISTED,
) -> TransactionRequest:
    return TransactionRequest(
        initiator="dave",
        source_vault="1",
        destination=destination,
        destination_type=destination_type,
        asset="USDC",
        amount_usd=Decimal(amount),
        submitted_at=T0,
        tx_type=TransactionType.TRANSFER,
    )


def test_sanctioned_destination_is_blocked(screening: ScreeningEngine):
    result = screening.screen(make_request(destination=ADDR_SANCTIONED))
    assert result.passed is False
    assert "sanctioned" in result.reason.lower()
    assert "OFAC_SANCTION" in result.categories


def test_high_risk_category_without_sanction_blocks_on_score(screening: ScreeningEngine):
    # Mixer: not a sanctioned category, but score 90 >= ceiling 75 -> blocked.
    result = screening.screen(make_request(destination=ADDR_MIXER))
    assert result.passed is False
    assert "risk score" in result.reason


def test_unknown_destination_is_clean(screening: ScreeningEngine):
    result = screening.screen(make_request(destination=ADDR_UNKNOWN))
    assert result.passed is True
    assert result.score == 0


def test_risk_score_boundary(screening: ScreeningEngine):
    # 74 passes (just under ceiling); 75 blocks (at ceiling).
    assert screening.screen(make_request(destination=ADDR_WATCH74)).passed is True
    assert screening.screen(make_request(destination=ADDR_WATCH75)).passed is False


def test_case_insensitive_address_lookup(screening: ScreeningEngine):
    result = screening.screen(make_request(destination=ADDR_SANCTIONED.lower()))
    assert result.passed is False


class TestTravelRule:
    def test_boundary_at_threshold_for_one_time(self, screening: ScreeningEngine):
        below = make_request(
            destination=ADDR_UNKNOWN, amount="999", destination_type=DestinationType.ONE_TIME
        )
        at = make_request(
            destination=ADDR_UNKNOWN, amount="1000", destination_type=DestinationType.ONE_TIME
        )
        assert screening.screen(below).travel_rule_required is False
        assert screening.screen(at).travel_rule_required is True

    def test_destination_type_dependence(self, screening: ScreeningEngine):
        # Same large amount, but a whitelisted destination does not trigger the flag.
        whitelisted = make_request(
            destination=ADDR_UNKNOWN, amount="50000", destination_type=DestinationType.WHITELISTED
        )
        one_time = make_request(
            destination=ADDR_UNKNOWN, amount="50000", destination_type=DestinationType.ONE_TIME
        )
        assert screening.screen(whitelisted).travel_rule_required is False
        assert screening.screen(one_time).travel_rule_required is True

    def test_travel_rule_does_not_block_clean_destination(self, screening: ScreeningEngine):
        # Travel-Rule is a flag, not a block: a clean one-time dest still passes.
        result = screening.screen(
            make_request(
                destination=ADDR_UNKNOWN, amount="5000", destination_type=DestinationType.ONE_TIME
            )
        )
        assert result.passed is True
        assert result.travel_rule_required is True
