from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from app.collectors.kamis import (
    KAMIS_PERIOD_URL,
    KamisParseError,
    KamisQuery,
    collect_period_prices,
    parse_period_prices,
)


FIXTURE = Path(__file__).parent / "fixtures" / "kamis_period.html"


def test_parse_period_prices_skips_summary_rows() -> None:
    prices = parse_period_prices(FIXTURE.read_text(encoding="utf-8"))

    assert len(prices) == 2
    assert prices[0].observed_on == date(2025, 3, 21)
    assert prices[0].price_won == 2443
    assert prices[0].change_rate == Decimal("-0.650671")


def test_parse_period_prices_detects_header_change() -> None:
    html = "<table><thead><tr><th>기준일</th><th>금액</th></tr></thead></table>"

    with pytest.raises(KamisParseError, match="표 헤더"):
        parse_period_prices(html)


@respx.mock
def test_collect_period_prices_sends_expected_query() -> None:
    route = respx.get(KAMIS_PERIOD_URL).mock(
        return_value=httpx.Response(200, text=FIXTURE.read_text(encoding="utf-8"))
    )
    query = KamisQuery(
        category_code="400",
        item_code="430",
        observed_on=date(2025, 3, 21),
    )

    prices = collect_period_prices(query)

    assert len(prices) == 2
    assert route.called
    request = route.calls[0].request
    assert request.url.params["action"] == "daily"
    assert request.url.params["regday"] == "2025.03.21"

