from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup


KAMIS_PERIOD_URL = "https://www.kamis.or.kr/customer/info/retail/period.do"


class KamisParseError(ValueError):
    """Raised when the KAMIS response no longer matches the expected contract."""


@dataclass(frozen=True)
class KamisPrice:
    observed_on: date
    price_won: int
    change_rate: Decimal


@dataclass(frozen=True)
class KamisQuery:
    category_code: str
    item_code: str
    observed_on: date
    kind_code: str = ""
    county_code: str = ""
    market_class_code: str = "01"
    product_rank_code: str = ""

    def as_params(self) -> dict[str, str]:
        return {
            "action": "daily",
            "countycode": self.county_code,
            "itemcategorycode": self.category_code,
            "itemcode": self.item_code,
            "kindcode": self.kind_code,
            "marketclscode": self.market_class_code,
            "productrankcode": self.product_rank_code,
            "regday": self.observed_on.strftime("%Y.%m.%d"),
        }


def _parse_date(value: str) -> date:
    normalized = " ".join(value.split()).replace(" ", "")
    for pattern in ("%Y.%m.%d", "%y.%m.%d"):
        try:
            return datetime.strptime(normalized, pattern).date()
        except ValueError:
            continue
    raise KamisParseError(f"지원하지 않는 날짜 형식입니다: {value!r}")


def _parse_price(value: str) -> int:
    normalized = value.replace(",", "").strip()
    try:
        return int(normalized)
    except ValueError as error:
        raise KamisParseError(f"가격을 정수로 변환할 수 없습니다: {value!r}") from error


def _parse_rate(value: str) -> Decimal:
    normalized = value.replace("%", "").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise KamisParseError(f"등락률을 숫자로 변환할 수 없습니다: {value!r}") from error


def parse_period_prices(html: str) -> list[KamisPrice]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise KamisParseError("가격 테이블을 찾을 수 없습니다.")

    headers = [cell.get_text(" ", strip=True) for cell in table.select("thead th")]
    if not headers:
        first_row = table.find("tr")
        headers = (
            [cell.get_text(" ", strip=True) for cell in first_row.find_all(["th", "td"])]
            if first_row
            else []
        )
    expected = ["날짜", "가격", "등락률"]
    if headers[:3] != expected:
        raise KamisParseError(f"예상하지 못한 표 헤더입니다: {headers[:3]!r}")

    prices: list[KamisPrice] = []
    for row in table.select("tbody tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) < 3:
            continue
        try:
            prices.append(
                KamisPrice(
                    observed_on=_parse_date(cells[0]),
                    price_won=_parse_price(cells[1]),
                    change_rate=_parse_rate(cells[2]),
                )
            )
        except KamisParseError:
            # Summary rows such as previous month/year averages are not observations.
            continue

    if not prices:
        raise KamisParseError("유효한 가격 행을 찾을 수 없습니다.")
    return prices


def collect_period_prices(
    query: KamisQuery,
    *,
    client: httpx.Client | None = None,
) -> list[KamisPrice]:
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            headers={"User-Agent": "food-market-data-pipeline/0.1"},
        )
    try:
        response = client.get(KAMIS_PERIOD_URL, params=query.as_params())
        response.raise_for_status()
        return parse_period_prices(response.text)
    finally:
        if owns_client:
            client.close()

