from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndicatorDefinition:
    indicator_id: str
    series_id: str
    name: str
    topic: str
    topic_icon: str
    unit: str
    unit_short: str
    frequency: str
    source_name: str
    source_url: str
    api_url: str
    dataset_code: str
    series_key: str
    dimensions: dict[str, str]
    description: str
    methodology: str
    limitations: str
    start_year: int = 1995
    yoy_threshold: float = 30.0
    comparable_eu: bool = True
    context_series_key: str = ""  # Multi-country key for Greece in context benchmark
    change_metric: str = "relative_percent"  # "relative_percent", "percentage_points", "disabled"
    known_missing_periods: dict[int, str] = field(default_factory=dict)  # Documented missing periods & reasons


# ==============================================================================
# Central Indicator Catalog
# ==============================================================================
INDICATOR_CATALOG: list[IndicatorDefinition] = [
    # --------------------------------------------------------------------------
    # 1. Economy
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="gdp_nominal",
        series_id="eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR",
        name="Gross Domestic Product (Nominal)",
        topic="Economy",
        topic_icon="🏛️",
        unit="Current prices, million euro (CP_MEUR)",
        unit_short="€M",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.EL?format=TSV",
        dataset_code="nama_10_gdp",
        series_key="A.CP_MEUR.B1GQ.EL",
        dimensions={"freq": "A", "unit": "CP_MEUR", "na_item": "B1GQ", "geo": "EL"},
        description="Total monetary value of all finished goods and services produced within Greece at current market prices.",
        methodology="European System of Accounts 2010 (ESA 2010), output/expenditure approach, compiled by ELSTAT and transmitted to Eurostat.",
        limitations="Values are unadjusted for inflation. Data prior to 1995 is missing in Eurostat's ESA 2010 table due to benchmark revision breaks.",
        start_year=1995,
        yoy_threshold=25.0,
        comparable_eu=True,
        context_series_key="A.CP_MEUR.B1GQ.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="gdp_real",
        series_id="eurostat.nama_10_gdp.EL.B1GQ.CLV20_MEUR",
        name="Gross Domestic Product (Real, Chain-linked 2020)",
        topic="Economy",
        topic_icon="🏛️",
        unit="Chain-linked volumes (2020), million euro (CLV20_MEUR)",
        unit_short="€M (vol)",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CLV20_MEUR.B1GQ.EL?format=TSV",
        dataset_code="nama_10_gdp",
        series_key="A.CLV20_MEUR.B1GQ.EL",
        dimensions={"freq": "A", "unit": "CLV20_MEUR", "na_item": "B1GQ", "geo": "EL"},
        description="Inflation-adjusted measure of Greek economic output benchmarked against constant 2020 prices.",
        methodology="ESA 2010 chain-linked volumes with reference year 2020, removing pure price changes across periods.",
        limitations="Chain-linked volume components are not strictly additive outside the reference year.",
        start_year=1995,
        yoy_threshold=20.0,
        comparable_eu=True,
        context_series_key="A.CLV20_MEUR.B1GQ.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="inflation_rate",
        series_id="eurostat.prc_hicp_aind.EL.RCH_A_AVG.CP00",
        name="Inflation Rate (HICP Annual Rate of Change)",
        topic="Economy",
        topic_icon="🏛️",
        unit="Annual average rate of change, percent (%)",
        unit_short="%",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_aind/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_aind/A.RCH_A_AVG.CP00.EL?format=TSV",
        dataset_code="prc_hicp_aind",
        series_key="A.RCH_A_AVG.CP00.EL",
        dimensions={"freq": "A", "unit": "RCH_A_AVG", "coicop": "CP00", "geo": "EL"},
        description="The Harmonised Index of Consumer Prices (HICP) annual average inflation rate across all household consumption items.",
        methodology="Harmonised EU Laspeyres-type consumer price index methodology across COICOP classification baskets.",
        limitations="Reflects average urban and rural consumption weights; expenditure weights are updated annually.",
        start_year=1996,
        yoy_threshold=5.0,
        comparable_eu=True,
        context_series_key="A.RCH_A_AVG.CP00.EL+EU27_2020+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
    ),
    IndicatorDefinition(
        indicator_id="unemployment_rate",
        series_id="eurostat.une_rt_a.EL.Y15-74.PC_ACT.T",
        name="Unemployment Rate (Age 15–74)",
        topic="Economy",
        topic_icon="🏛️",
        unit="Percentage of active population (%)",
        unit_short="%",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/une_rt_a/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/une_rt_a/A.Y15-74.PC_ACT.T.EL?format=TSV",
        dataset_code="une_rt_a",
        series_key="A.Y15-74.PC_ACT.T.EL",
        dimensions={"freq": "A", "age": "Y15-74", "unit": "PC_ACT", "sex": "T", "geo": "EL"},
        description="Proportion of the economically active civilian population (labor force aged 15–74) currently without work and actively seeking employment.",
        methodology="EU Labour Force Survey (LFS) harmonized definition (ILO standards) compiled by ELSTAT.",
        limitations="LFS methodology was revised under the Integrated European Social Statistics (IESS) framework in 2021, creating a minor break in series.",
        start_year=2009,
        yoy_threshold=4.0,
        comparable_eu=True,
        context_series_key="A.Y15-74.PC_ACT.T.EL+EU27_2020+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
    ),
    IndicatorDefinition(
        indicator_id="public_debt_pct",
        series_id="eurostat.gov_10dd_edpt1.EL.PC_GDP.S13.GD",
        name="General Government Gross Debt (% of GDP)",
        topic="Economy",
        topic_icon="🏛️",
        unit="Percentage of GDP (%)",
        unit_short="% GDP",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/gov_10dd_edpt1/A.PC_GDP.S13.GD.EL?format=TSV",
        dataset_code="gov_10dd_edpt1",
        series_key="A.PC_GDP.S13.GD.EL",
        dimensions={"freq": "A", "unit": "PC_GDP", "sector": "S13", "na_item": "GD", "geo": "EL"},
        description="Total general government gross debt as a percentage of gross domestic product under Maastricht Treaty excessive deficit procedure definitions.",
        methodology="Maastricht debt definition: consolidated general government liabilities in currency and deposits, debt securities, and loans at nominal value.",
        limitations="Denominator is nominal GDP; high GDP inflation can mechanically compress the ratio even if debt stock rises.",
        start_year=1995,
        yoy_threshold=15.0,
        comparable_eu=True,
        context_series_key="A.PC_GDP.S13.GD.EL+EU27_2020+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
    ),
    IndicatorDefinition(
        indicator_id="trade_exports",
        series_id="eurostat.nama_10_gdp.EL.P6.CP_MEUR",
        name="Exports of Goods and Services",
        topic="Economy",
        topic_icon="🏛️",
        unit="Current prices, million euro (CP_MEUR)",
        unit_short="€M",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.P6.EL?format=TSV",
        dataset_code="nama_10_gdp",
        series_key="A.CP_MEUR.P6.EL",
        dimensions={"freq": "A", "unit": "CP_MEUR", "na_item": "P6", "geo": "EL"},
        description="Total value of Greek goods and commercial services exported to international trading partners, including shipping and tourism.",
        methodology="ESA 2010 National Accounts item P6 (Exports of goods and services), current market prices.",
        limitations="Denominated in current prices; includes substantial shipping freight and international tourism service flows.",
        start_year=1995,
        yoy_threshold=30.0,
        comparable_eu=True,
        context_series_key="A.CP_MEUR.P6.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="trade_imports",
        series_id="eurostat.nama_10_gdp.EL.P7.CP_MEUR",
        name="Imports of Goods and Services",
        topic="Economy",
        topic_icon="🏛️",
        unit="Current prices, million euro (CP_MEUR)",
        unit_short="€M",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.P7.EL?format=TSV",
        dataset_code="nama_10_gdp",
        series_key="A.CP_MEUR.P7.EL",
        dimensions={"freq": "A", "unit": "CP_MEUR", "na_item": "P7", "geo": "EL"},
        description="Total value of foreign goods and commercial services imported into the Greek economy.",
        methodology="ESA 2010 National Accounts item P7 (Imports of goods and services), current market prices.",
        limitations="Subject to international energy price shocks and supply chain price fluctuations.",
        start_year=1995,
        yoy_threshold=30.0,
        comparable_eu=True,
        context_series_key="A.CP_MEUR.P7.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),

    # --------------------------------------------------------------------------
    # 2. People & Society
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="population",
        series_id="eurostat.demo_pjan.EL.NR.TOTAL.T",
        name="Total Population (1 January)",
        topic="People & Society",
        topic_icon="👥",
        unit="Number of persons (NR)",
        unit_short="pers.",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/demo_pjan/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_pjan/A.NR.TOTAL.T.EL?format=TSV",
        dataset_code="demo_pjan",
        series_key="A.NR.TOTAL.T.EL",
        dimensions={"freq": "A", "unit": "NR", "age": "TOTAL", "sex": "T", "geo": "EL"},
        description="Usually resident population of Greece on 1 January of each reference year.",
        methodology="Census benchmarks adjusted annually using civil vital statistics (births/deaths) and net migration registers.",
        limitations="Post-census revisions occur after decennial census results (e.g., 2011 and 2021 censuses).",
        start_year=1960,
        yoy_threshold=5.0,
        comparable_eu=True,
        context_series_key="A.NR.TOTAL.T.EL+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="life_expectancy",
        series_id="eurostat.demo_mlexpec.EL.YR.T.Y_LT1",
        name="Life Expectancy at Birth",
        topic="People & Society",
        topic_icon="👥",
        unit="Years (YR)",
        unit_short="years",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/demo_mlexpec/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_mlexpec/A.YR.T.Y_LT1.EL?format=TSV",
        dataset_code="demo_mlexpec",
        series_key="A.YR.T.Y_LT1.EL",
        dimensions={"freq": "A", "unit": "YR", "sex": "T", "age": "Y_LT1", "geo": "EL"},
        description="The mean number of years a newborn child can expect to live if subjected throughout life to current mortality conditions.",
        methodology="Period life tables calculated from age-specific mortality rates across Greek demographic records.",
        limitations="Sensitive to exceptional annual excess mortality events (e.g. 2020-2022 pandemic mortality dip).",
        start_year=1961,
        yoy_threshold=5.0,
        comparable_eu=True,
        context_series_key="A.YR.T.Y_LT1.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="poverty_rate",
        series_id="eurostat.ilc_li02.EL.MED_EI.PC.B_60.T.TOTAL",
        name="At-Risk-of-Poverty Rate (60% Median Income)",
        topic="People & Society",
        topic_icon="👥",
        unit="Percentage of population (%)",
        unit_short="%",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/ilc_li02/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/ilc_li02/A.MED_EI.PC.B_60.T.TOTAL.EL?format=TSV",
        dataset_code="ilc_li02",
        series_key="A.MED_EI.PC.B_60.T.TOTAL.EL",
        dimensions={"freq": "A", "statinfo": "MED_EI", "unit": "PC", "rskpovth": "B_60", "sex": "T", "age": "TOTAL", "geo": "EL"},
        description="Share of people with an equivalised disposable income below the risk-of-poverty threshold (set at 60% of the national median equivalised disposable income).",
        methodology="EU Statistics on Income and Living Conditions (EU-SILC) survey microdata.",
        limitations="Relative poverty metric; if overall national median income drops during recessions, the threshold drops as well.",
        start_year=1995,
        yoy_threshold=4.0,
        comparable_eu=True,
        context_series_key="A.MED_EI.PC.B_60.T.TOTAL.EL+EU27_2020+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
        known_missing_periods={
            2002: "Documented EU-wide survey transition gap between ECHP (ended 2001) and EU-SILC (launched in Greece in 2003 under Regulation EC 1177/2003)."
        },
    ),
    IndicatorDefinition(
        indicator_id="immigration_flow",
        series_id="eurostat.migr_imm1ctz.EL.TOTAL.COMPLET.TOTAL.NR.T",
        name="Annual Immigration Inflow",
        topic="People & Society",
        topic_icon="👥",
        unit="Number of persons (NR)",
        unit_short="pers.",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/migr_imm1ctz/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/migr_imm1ctz/A.TOTAL.COMPLET.TOTAL.NR.T.EL?format=TSV",
        dataset_code="migr_imm1ctz",
        series_key="A.TOTAL.COMPLET.TOTAL.NR.T.EL",
        dimensions={"freq": "A", "citizen": "TOTAL", "agedef": "COMPLET", "age": "TOTAL", "unit": "NR", "sex": "T", "geo": "EL"},
        description="Number of long-term immigrants establishing usual residence in Greece for a period of at least 12 months.",
        methodology="UN and Regulation (EC) 862/2007 harmonized migration statistics from administrative registers and residence permits.",
        limitations="Does not include short-term circular movements or undocumented border crossings without resident status.",
        start_year=1998,
        yoy_threshold=40.0,
        comparable_eu=True,
        context_series_key="A.TOTAL.COMPLET.TOTAL.NR.T.EL+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="emigration_flow",
        series_id="eurostat.migr_emi1ctz.EL.TOTAL.COMPLET.TOTAL.NR.T",
        name="Annual Emigration Outflow",
        topic="People & Society",
        topic_icon="👥",
        unit="Number of persons (NR)",
        unit_short="pers.",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/migr_emi1ctz/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/migr_emi1ctz/A.TOTAL.COMPLET.TOTAL.NR.T.EL?format=TSV",
        dataset_code="migr_emi1ctz",
        series_key="A.TOTAL.COMPLET.TOTAL.NR.T.EL",
        dimensions={"freq": "A", "citizen": "TOTAL", "agedef": "COMPLET", "age": "TOTAL", "unit": "NR", "sex": "T", "geo": "EL"},
        description="Number of usual residents departing Greece with the intention of remaining abroad for at least 12 months.",
        methodology="Estimation based on deregistration registers and partner country immigration records.",
        limitations="Under-registration of departures is a common challenge across demographic statistical institutes.",
        start_year=1998,
        yoy_threshold=40.0,
        comparable_eu=True,
        context_series_key="A.TOTAL.COMPLET.TOTAL.NR.T.EL+DE+IT+ES+PT+CY",
    ),

    # --------------------------------------------------------------------------
    # 3. Energy & Environment
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="renewable_energy_share",
        series_id="eurostat.nrg_ind_ren.EL.REN.PC",
        name="Renewable Energy Share",
        topic="Energy & Environment",
        topic_icon="⚡",
        unit="Percentage of gross final energy consumption (%)",
        unit_short="%",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_ren/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nrg_ind_ren/A.REN.PC.EL?format=TSV",
        dataset_code="nrg_ind_ren",
        series_key="A.REN.PC.EL",
        dimensions={"freq": "A", "nrg_bal": "REN", "unit": "PC", "geo": "EL"},
        description="Share of energy from renewable sources in gross final energy consumption across electricity, heating/cooling, and transport.",
        methodology="Calculated under Directive (EU) 2018/2001 (RED II) guidelines based on national energy balances.",
        limitations="Hydro and wind normalization rules are applied to smooth climatic weather fluctuations across years.",
        start_year=2004,
        yoy_threshold=5.0,
        comparable_eu=True,
        context_series_key="A.REN.PC.EL+EU27_2020+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
    ),
    IndicatorDefinition(
        indicator_id="ghg_emissions",
        series_id="eurostat.env_air_gge.EL.THS_T.GHG.TOTXMEMO",
        name="Greenhouse Gas Emissions",
        topic="Energy & Environment",
        topic_icon="⚡",
        unit="Thousand tonnes CO2 equivalent (THS_T)",
        unit_short="kt CO2e",
        frequency="Annual",
        source_name="Eurostat / European Environment Agency (EEA)",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/env_air_gge/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/env_air_gge/A.THS_T.GHG.TOTXMEMO.EL?format=TSV",
        dataset_code="env_air_gge",
        series_key="A.THS_T.GHG.TOTXMEMO.EL",
        dimensions={"freq": "A", "unit": "THS_T", "airpol": "GHG", "src_crf": "TOTXMEMO", "geo": "EL"},
        description="Total Greek emissions of greenhouse gases (CO2, N2O, CH4, HFC, PFC, SF6, NF3) expressed in thousand tonnes of CO2 equivalent.",
        methodology="UNFCCC reporting guidelines and IPCC 2006 guidelines, excluding international aviation memo items and LULUCF.",
        limitations="Official inventory submissions have an approximate 18-month reporting lag to complete quality control.",
        start_year=1990,
        yoy_threshold=20.0,
        comparable_eu=True,
        context_series_key="A.THS_T.GHG.TOTXMEMO.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="energy_consumption",
        series_id="eurostat.nrg_ind_eff.EL.FEC_EED.MTOE",
        name="Final Energy Consumption",
        topic="Energy & Environment",
        topic_icon="⚡",
        unit="Million tonnes of oil equivalent (MTOE)",
        unit_short="MTOE",
        frequency="Annual",
        source_name="Eurostat",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_eff/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nrg_ind_eff/A.FEC_EED.MTOE.EL?format=TSV",
        dataset_code="nrg_ind_eff",
        series_key="A.FEC_EED.MTOE.EL",
        dimensions={"freq": "A", "nrg_bal": "FEC_EED", "unit": "MTOE", "geo": "EL"},
        description="Total energy consumed by end users across Greek industry, transport, households, services, and agriculture under the Energy Efficiency Directive.",
        methodology="Energy Efficiency Directive (Directive 2012/27/EU as amended) energy balance accounting.",
        limitations="Excludes energy transformation sector and transmission losses.",
        start_year=2005,
        yoy_threshold=20.0,
        comparable_eu=True,
        context_series_key="A.FEC_EED.MTOE.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),

    # --------------------------------------------------------------------------
    # 4. Tourism
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="tourist_arrivals",
        series_id="eurostat.tour_occ_arnat.EL.TOTAL.NR.I551-I553",
        name="Tourist Arrivals (All Accommodation)",
        topic="Tourism",
        topic_icon="🏖️",
        unit="Number of arrivals (NR)",
        unit_short="arrivals",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/tour_occ_arnat/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/tour_occ_arnat/A.TOTAL.NR.I551-I553.EL?format=TSV",
        dataset_code="tour_occ_arnat",
        series_key="A.TOTAL.NR.I551-I553.EL",
        dimensions={"freq": "A", "c_resid": "TOTAL", "unit": "NR", "nace_r2": "I551-I553", "geo": "EL"},
        description="Total tourist arrivals registered at hotels, holiday accommodation, and campsites throughout Greece.",
        methodology="Regulation (EU) No 692/2011 on tourism statistics; accommodation census and sample surveys conducted by ELSTAT.",
        limitations="Counts formal tourist accommodations (NACE I551–I553); informal peer-to-peer short term rentals are recorded separately.",
        start_year=1994,
        yoy_threshold=35.0,
        comparable_eu=True,
        context_series_key="A.TOTAL.NR.I551-I553.EL+DE+IT+ES+PT+CY",
    ),
    IndicatorDefinition(
        indicator_id="tourist_nights",
        series_id="eurostat.tour_occ_ninat.EL.TOTAL.NR.I551-I553",
        name="Tourist Overnight Stays (Nights Spent)",
        topic="Tourism",
        topic_icon="🏖️",
        unit="Number of nights (NR)",
        unit_short="nights",
        frequency="Annual",
        source_name="Eurostat / ELSTAT",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/tour_occ_ninat/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/tour_occ_ninat/A.TOTAL.NR.I551-I553.EL?format=TSV",
        dataset_code="tour_occ_ninat",
        series_key="A.TOTAL.NR.I551-I553.EL",
        dimensions={"freq": "A", "c_resid": "TOTAL", "unit": "NR", "nace_r2": "I551-I553", "geo": "EL"},
        description="Total number of nights spent by tourists (domestic and international) in Greek tourist accommodation establishments.",
        methodology="Regulation (EU) No 692/2011; monthly guest register reports compiled by ELSTAT.",
        limitations="High seasonal concentration during Q3 summer peak.",
        start_year=1994,
        yoy_threshold=35.0,
        comparable_eu=True,
        context_series_key="A.TOTAL.NR.I551-I553.EL+DE+IT+ES+PT+CY",
    ),

    # --------------------------------------------------------------------------
    # 5. Housing
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="house_price_index",
        series_id="eurostat.tipsho20.EL.I15_A_AVG",
        name="House Price Index (Nominal, 2015=100)",
        topic="Housing",
        topic_icon="🏠",
        unit="Annual average index (2015=100)",
        unit_short="idx (2015=100)",
        frequency="Annual",
        source_name="Eurostat / Bank of Greece",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/tipsho20/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/tipsho20/A.I15_A_AVG.EL?format=TSV",
        dataset_code="tipsho20",
        series_key="A.I15_A_AVG.EL",
        dimensions={"freq": "A", "unit": "I15_A_AVG", "geo": "EL"},
        description="Official index tracking changes in transaction prices for all residential properties purchased by households in Greece.",
        methodology="Macroeconomic Imbalance Procedure (MIP) nominal House Price Index, compiled from Bank of Greece credit institution appraisal data.",
        limitations="Observations carry official Eurostat estimated/provisional flags ('ep') reflecting ongoing appraisal model calibration.",
        start_year=2000,
        yoy_threshold=20.0,
        comparable_eu=True,
        context_series_key="A.I15_A_AVG.EL+EU27_2020+DE+IT+ES+PT+CY",
    ),

    # --------------------------------------------------------------------------
    # 6. Banking & Finance
    # --------------------------------------------------------------------------
    IndicatorDefinition(
        indicator_id="bond_yield_10y",
        series_id="eurostat.irt_lt_mcby_a.EL.MCBY",
        name="10-Year Government Benchmark Bond Yield",
        topic="Banking & Finance",
        topic_icon="🏦",
        unit="Percentage per annum (%)",
        unit_short="%",
        frequency="Annual",
        source_name="Eurostat / European Central Bank",
        source_url="https://ec.europa.eu/eurostat/databrowser/view/irt_lt_mcby_a/default/table?lang=en",
        api_url="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/irt_lt_mcby_a/A.MCBY.EL?format=TSV",
        dataset_code="irt_lt_mcby_a",
        series_key="A.MCBY.EL",
        dimensions={"freq": "A", "int_rt": "MCBY", "geo": "EL"},
        description="Long-term sovereign bond yield on Greek central government 10-year benchmark securities, defined under the Maastricht convergence criteria.",
        methodology="EMU convergence criterion methodology: annual arithmetic average of daily secondary market benchmark bond yields.",
        limitations="During the sovereign debt restructuring period (2011–2015), bond liquidity was constrained, causing elevated nominal yields.",
        start_year=1992,
        yoy_threshold=4.0,
        comparable_eu=True,
        context_series_key="A.MCBY.EL+DE+IT+ES+PT+CY",
        change_metric="percentage_points",
    ),
]

# Quick access lookups
CATALOG_BY_ID: dict[str, IndicatorDefinition] = {
    ind.indicator_id: ind for ind in INDICATOR_CATALOG
}

CATALOG_BY_SERIES_ID: dict[str, IndicatorDefinition] = {
    ind.series_id: ind for ind in INDICATOR_CATALOG
}

ALL_TOPICS: list[str] = [
    "Economy",
    "People & Society",
    "Energy & Environment",
    "Tourism",
    "Housing",
    "Banking & Finance",
]

TOPIC_ICONS: dict[str, str] = {
    "Economy": "🏛️",
    "People & Society": "👥",
    "Energy & Environment": "⚡",
    "Tourism": "🏖️",
    "Housing": "🏠",
    "Banking & Finance": "🏦",
}


# ==============================================================================
# Documented Limitations & Excluded Topics / Special Methodologies
# ==============================================================================
TOPIC_LIMITATIONS_DOCUMENTATION: dict[str, dict[str, Any]] = {
    "tourism_receipts": {
        "topic": "Tourism",
        "indicator_label": "Tourism Receipts (Travel Services Balance)",
        "official_authority": "Bank of Greece (BoG) - Balance of Payments / Travel Services",
        "direct_link": "https://www.bankofgreece.gr/en/statistics/external-sector/balance-of-payments",
        "access_method": "Published in monthly PDF and Excel bulletin tables (Table 14: Travel Services Balance).",
        "why_not_direct_api": (
            "The Bank of Greece publishes monthly travel receipts and expenditures in periodic statistical "
            "press releases and downloadable Excel workbooks without providing a public, unauthenticated, "
            "machine-readable REST API. In keeping with our strict zero-placeholder policy, rather than fabricating "
            "receipt figures or guessing series codes, we monitor official accommodation volumes (arrivals and nights) "
            "via Eurostat's verified API and document the Bank of Greece's official publication channel here."
        ),
    },
    "retail_banking_rates": {
        "topic": "Banking & Finance",
        "indicator_label": "Retail Household Deposit & Lending Rates",
        "official_authority": "European Central Bank (ECB) & Bank of Greece - MFI Interest Rate (MIR) Statistics",
        "direct_link": "https://data.ecb.europa.eu/data/datasets/MIR",
        "access_method": "ECB Data Portal MFI Interest Rates dataset (Dataflow MIR: M.GR.B.L21 for deposits, M.GR.B.A20 for loans).",
        "why_not_direct_api": (
            "Greek retail bank interest rates are governed by ECB MFI interest rate regulations and published "
            "at high monthly frequency across hundreds of granular instrument dimensions (maturities, amounts, fixation periods). "
            "Our primary surveillance focuses on the 10-Year Sovereign Benchmark Yield (which anchors national borrowing costs). "
            "Users requiring loan-by-loan retail breakdown should reference the ECB MIR portal directly."
        ),
    },
    "electricity_prices": {
        "topic": "Energy & Environment",
        "indicator_label": "Household Electricity Prices (Band DC: 2,500 - 5,000 kWh)",
        "official_authority": "Eurostat (Energy Statistics - dataset nrg_pc_204)",
        "direct_link": "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table?lang=en",
        "access_method": "Eurostat bi-annual semester reporting (S1: Jan-Jun, S2: Jul-Dec).",
        "why_not_direct_api": (
            "Eurostat disseminates electricity retail prices on a bi-annual semester basis (EUR/kWh all taxes included) "
            "rather than standard calendar year matrices. Because our primary database engine tracks annual calendar "
            "series, the semester data is documented in methodology to preserve calendar integrity."
        ),
    },
}
