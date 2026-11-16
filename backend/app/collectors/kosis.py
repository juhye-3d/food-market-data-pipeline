from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx


KOSIS_DATA_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
KOSIS_ORG_ID = "101"
KOSIS_TABLE_ID = "DT_1F02031"
FOOD_MANUFACTURING_CODE = "C10"
RAW_INDEX_ITEM_IDS = ("T10", "T11", "T12")


class KosisResponseError(ValueError):
    """Raised when KOSIS returns data outside the expected contract."""


@dataclass(frozen=True)
class KosisIndustryIndex:
    region_code: str
    region_name: str
    industry_code: str
    industry_name: str
    item_id: str
    item_name: str
    period: str
    value: Decimal
    unit: str
    source_updated_on: str

    @property
    def natural_key(self) -> tuple[str, str, str, str]:
        return (self.region_code, self.industry_code, self.item_id, self.period)


@dataclass(frozen=True)
class KosisQuery:
    start_period: str
    end_period: str

    def __post_init__(self) -> None:
        for name, value in (
            ("start_period", self.start_period),
            ("end_period", self.end_period),
        ):
            try:
                datetime.strptime(value, "%Y%m")
            except ValueError as error:
                raise ValueError(f"{name}은 YYYYMM 형식이어야 합니다: {value!r}") from error
        if self.start_period > self.end_period:
            raise ValueError("start_period는 end_period보다 늦을 수 없습니다.")

    def as_params(self, api_key: str) -> dict[str, str]:
        return {
            "method": "getList",
            "apiKey": api_key,
            "orgId": KOSIS_ORG_ID,
            "tblId": KOSIS_TABLE_ID,
            "objL1": "ALL",
            "objL2": FOOD_MANUFACTURING_CODE,
            "itmId": "+".join(RAW_INDEX_ITEM_IDS),
            "prdSe": "M",
            "startPrdDe": self.start_period,
            "endPrdDe": self.end_period,
            "format": "json",
            "jsonVD": "Y",
        }


def parse_industry_indices(payload: object) -> list[KosisIndustryIndex]:
    if not isinstance(payload, list):
        raise KosisResponseError("KOSIS 응답이 JSON 배열이 아닙니다.")

    rows: list[KosisIndustryIndex] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise KosisResponseError(f"{index}번째 행이 객체가 아닙니다.")
        required = (
            "C1",
            "C1_NM",
            "C2",
            "C2_NM",
            "ITM_ID",
            "ITM_NM",
            "PRD_DE",
            "DT",
            "UNIT_NM",
            "LST_CHN_DE",
        )
        missing = [field for field in required if not item.get(field)]
        if missing:
            raise KosisResponseError(f"{index}번째 행의 필수 필드 누락: {missing}")
        try:
            value = Decimal(str(item["DT"]))
        except InvalidOperation as error:
            raise KosisResponseError(
                f"{index}번째 행의 수치를 변환할 수 없습니다: {item['DT']!r}"
            ) from error
        rows.append(
            KosisIndustryIndex(
                region_code=str(item["C1"]),
                region_name=str(item["C1_NM"]),
                industry_code=str(item["C2"]),
                industry_name=str(item["C2_NM"]),
                item_id=str(item["ITM_ID"]),
                item_name=str(item["ITM_NM"]),
                period=str(item["PRD_DE"]),
                value=value,
                unit=str(item["UNIT_NM"]),
                source_updated_on=str(item["LST_CHN_DE"]),
            )
        )
    return rows


def collect_industry_indices(
    api_key: str,
    query: KosisQuery,
    *,
    client: httpx.Client | None = None,
) -> list[KosisIndustryIndex]:
    if not api_key:
        raise ValueError("KOSIS_API_KEY가 필요합니다.")
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=httpx.Timeout(30.0), follow_redirects=True)
    try:
        response = client.get(KOSIS_DATA_URL, params=query.as_params(api_key))
        response.raise_for_status()
        return parse_industry_indices(response.json())
    finally:
        if owns_client:
            client.close()

