from __future__ import annotations

import pytest

from greek_data_monitor.ingestion import IngestionError, parse_multi_country_tsv

SAMPLE_MULTI_COUNTRY_TSV = (
    "freq,age,unit,sex,geo\\TIME_PERIOD\t2020 \t2021 \t2022 \t2023 \n"
    "A,Y15-74,PC_ACT,T,CY\t7.6 \t7.5 \t6.8 \t6.1 \n"
    "A,Y15-74,PC_ACT,T,DE\t3.7 \t3.6 \t3.1 \t3.0 \n"
    "A,Y15-74,PC_ACT,T,EL\t17.6 \t14.8 \t12.5 \t11.1 \n"
    "A,Y15-74,PC_ACT,T,ES\t15.5 \t14.8 \t12.9 \t12.1 \n"
    "A,Y15-74,PC_ACT,T,EU27_2020\t7.2 \t7.0 \t6.1 \t6.0 \n"
    "A,Y15-74,PC_ACT,T,IT\t9.3 \t9.5 \t8.1 \t7.7 \n"
    "A,Y15-74,PC_ACT,T,PT\t7.0 \t6.6 \t6.0 \t6.5 \n"
)


def test_parse_multi_country_tsv_success() -> None:
    benchmarks = parse_multi_country_tsv(SAMPLE_MULTI_COUNTRY_TSV, indicator_id="unemployment_rate")
    assert len(benchmarks) == 7 * 4  # 7 countries x 4 periods

    # Check Greece values
    el_records = [b for b in benchmarks if b["country_code"] == "EL"]
    assert len(el_records) == 4
    assert el_records[0]["country_name"] == "Greece"
    assert el_records[0]["period"] == 2020
    assert el_records[0]["value"] == 17.6

    # Check EU27 average values
    eu_records = [b for b in benchmarks if b["country_code"] == "EU27_2020"]
    assert len(eu_records) == 4
    assert eu_records[0]["country_name"] == "European Union (EU-27)"
    assert eu_records[3]["period"] == 2023
    assert eu_records[3]["value"] == 6.0


def test_parse_multi_country_tsv_with_flags_and_missing() -> None:
    tsv_with_flags = (
        "freq,unit,geo\\TIME_PERIOD\t2021 \t2022 \n"
        "A,I15_A_AVG,EL\t118.60 e\t132.76 ep\n"
        "A,I15_A_AVG,DE\t: \t162.10 \n"
    )
    benchmarks = parse_multi_country_tsv(tsv_with_flags, indicator_id="house_price_index")
    assert len(benchmarks) == 4

    el_2022 = next(b for b in benchmarks if b["country_code"] == "EL" and b["period"] == 2022)
    assert el_2022["value"] == 132.76
    assert el_2022["source_status"] == "ep"

    de_2021 = next(b for b in benchmarks if b["country_code"] == "DE" and b["period"] == 2021)
    assert de_2021["value"] is None


def test_parse_multi_country_tsv_empty_raises() -> None:
    with pytest.raises(IngestionError, match="empty response"):
        parse_multi_country_tsv("")
