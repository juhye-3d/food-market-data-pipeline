from decimal import Decimal

import pytest

from app.collectors.kosis import (
    KosisQuery,
    KosisResponseError,
    parse_industry_indices,
)


SAMPLE_ROW = {
    "C1": "41",
    "C1_NM": "수도권",
    "C2": "C10",
    "C2_NM": "식료품 제조업",
    "ITM_ID": "T10",
    "ITM_NM": "산업생산지수(원지수)",
    "PRD_DE": "202601",
    "DT": "105",
    "UNIT_NM": "2020＝100",
    "LST_CHN_DE": "2026-08-05",
}


def test_parse_industry_indices_builds_natural_key() -> None:
    rows = parse_industry_indices([SAMPLE_ROW])

    assert rows[0].value == Decimal("105")
    assert rows[0].natural_key == ("41", "C10", "T10", "202601")


def test_parse_industry_indices_rejects_missing_required_field() -> None:
    invalid = {**SAMPLE_ROW, "DT": ""}

    with pytest.raises(KosisResponseError, match="필수 필드 누락"):
        parse_industry_indices([invalid])


def test_kosis_query_validates_period_range() -> None:
    with pytest.raises(ValueError, match="늦을 수 없습니다"):
        KosisQuery(start_period="202603", end_period="202601")

