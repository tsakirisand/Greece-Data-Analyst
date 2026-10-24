from __future__ import annotations

import io
from datetime import date
from math import isfinite
import sys
from pathlib import Path
from typing import Any

# Prefer the package shipped with this checkout over any stale copy installed
# in the deployment environment. Streamlit Cloud executes app.py from the repo
# root, while this project keeps its package under src/.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from greek_data_monitor.catalog import (
    ALL_TOPICS,
    CATALOG_BY_ID,
    CATALOG_BY_SERIES_ID,
    INDICATOR_CATALOG,
    TOPIC_ICONS,
    TOPIC_LIMITATIONS_DOCUMENTATION,
    IndicatorDefinition,
)
from greek_data_monitor.config import AVAILABLE_SERIES, DEFAULT_SERIES, Settings
from greek_data_monitor.dashboard_service import (
    calculate_annual_change,
    calculate_indicator_correlation_matrix,
    calculate_quality_scorecard,
    calculate_safe_comparison,
    calculate_statistical_anomalies,
    compare_run_snapshots,
    filter_and_sort_observations,
    format_check_age,
    format_source_status,
    format_gdp_value,
    format_indicator_value,
    generate_markdown_audit_report,
    get_flag_descriptions,
    get_greek_economic_milestones,
    get_overview_kpis,
    get_quality_rule_descriptions,
    get_what_changed_summary,
    sync_all_indicators,
)
from greek_data_monitor.ingestion import (
    COUNTRY_FLAGS,
    COUNTRY_NAMES,
    IngestionError,
    fetch_eurostat_series,
    fetch_indicator_benchmarks,
)
from greek_data_monitor.i18n import configure_language, translate_text
from greek_data_monitor.quality import inspect
from greek_data_monitor.store import (
    get_all_series_status,
    get_country_benchmarks,
    get_latest_observations,
    get_run_details,
    list_runs,
    save_country_benchmarks,
    save_run,
)

st.set_page_config(
    page_title="Greek Public Data Quality Monitor",
    page_icon="🇬🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

language_choice = st.sidebar.selectbox(
    "Language / Γλώσσα",
    ["English", "Ελληνικά"],
    key="app_language",
)
greek_language = language_choice == "Ελληνικά"
configure_language(greek_language)

# Custom Accessible Dark-Themed CSS styling
st.markdown(
    """
    <style>
    .brand-title {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.15rem;
    }
    .brand-subtitle {
        color: #94a3b8;
        font-size: 0.98rem;
        margin-bottom: 1.2rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1;
        letter-spacing: 0.02em;
    }
    .badge-pass { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 9999px; }
    .badge-warn { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 9999px; }
    .badge-error { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 9999px; }
    .badge-info { background-color: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 9999px; }
    .badge-stale { background-color: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.35); border-radius: 9999px; }
    .card-kpi {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-left: 3.5px solid #0284c7;
        border-radius: 0 0.5rem 0.5rem 0;
        padding: 0.5rem 0.75rem;
        height: 88px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.25);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .card-kpi:hover {
        background: rgba(30, 41, 59, 0.7);
        border-color: rgba(56, 189, 248, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 8px 22px -3px rgba(2, 132, 199, 0.25);
    }
    .card-kpi-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        line-height: 1;
    }
    .card-kpi-topic {
        color: #94a3b8;
        font-size: 0.63rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.9;
    }
    .card-kpi-title {
        color: #e2e8f0;
        font-size: 0.78rem;
        font-weight: 500;
        line-height: 1.15;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .card-kpi-val {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.01em;
        margin: 0.02rem 0;
        display: flex;
        align-items: baseline;
        gap: 0.25rem;
        line-height: 1.1;
    }
    .card-kpi-sub {
        font-size: 0.68rem;
        color: #94a3b8;
        line-height: 1.1;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .callout-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-left: 4px solid #0284c7;
        padding: 0.85rem 1.1rem;
        border-radius: 0 0.5rem 0.5rem 0;
        margin-bottom: 1.2rem;
        font-size: 0.92rem;
        color: #e2e8f0;
    }
    .callout-box code {
        background: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #334155;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .scorecard-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 0.75rem;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = Settings()

# ---------------------------------------------------------
# Sidebar: Navigation & Controls
# ---------------------------------------------------------
st.sidebar.markdown("### 🇬🇷 Data Quality Monitor")
st.sidebar.caption("Multi-Topic Official Public Data Surveillance")

# Surveillance, analysis, and interpretation pages
page = st.sidebar.radio(
    "Navigation",
    options=[
        "📌 Overview",
        "🔍 Explore Data",
        "🇪🇺 Greece in Context",
        "🏛️ Fiscal & Debt Surveillance",
        "🔬 Cross-Series Analysis & Lab",
        "🛡️ Data Quality & Freshness",
        "📑 Audit Reports & Data Export",
        "📈 Greece: Progress & Challenges",
        "ℹ️ Sources & Methodology",
    ],
    index=0,
    format_func=translate_text,
)

st.sidebar.markdown("---")

# Settings & Thresholds
with st.sidebar.expander("⚙️ Settings & Database", expanded=False):
    db_url = st.text_input("Database URL", value=settings.database_url)
    default_timeout = st.number_input("HTTP Timeout (seconds)", min_value=5, max_value=120, value=settings.request_timeout_seconds)

# Ingestion Triggers
st.sidebar.markdown("### 🔄 Ingestion & Refresh")
if st.sidebar.button("🚀 Sync All Indicators (19)", type="primary", use_container_width=True, help="Fetch and validate all catalog indicators independently."):
    with st.spinner("Connecting to official Eurostat APIs across all topics..."):
        sync_result = sync_all_indicators(db_url, timeout=int(default_timeout))
        st.sidebar.success(f"Synced {sync_result['success']}/{sync_result['total']} indicators!")
        if sync_result['failed'] > 0:
            st.sidebar.warning(f"{sync_result['failed']} indicator(s) reported upstream issues.")
        st.rerun()

# Check Database Content
all_status = get_all_series_status(db_url)
if not all_status:
    # If database is fresh/empty, provide clear onboarding banner
    st.markdown('<div class="brand-title">🇬🇷 Greek Public Data Quality Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Genuinely multi-topic public data surveillance for Greece</div>', unsafe_allow_html=True)
    st.warning("Database contains no stored observations yet.")
    st.info("Click **'🚀 Sync All Indicators'** in the sidebar to perform the initial ingestion of official data from Eurostat.")
    if st.button("🚀 Run Initial Sync Now", type="primary"):
        with st.spinner("Ingesting verified datasets across Economy, Society, Energy, Tourism, Housing, and Finance..."):
            sync_result = sync_all_indicators(db_url, timeout=int(default_timeout))
            st.success(f"Successfully ingested {sync_result['success']} indicators!")
            st.rerun()
    st.stop()


# ==============================================================================
# PAGE 1: 📌 OVERVIEW
# ==============================================================================
if page == "📌 Overview":
    st.markdown('<div class="brand-title">🇬🇷 Greece Overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Cross-topic statistical surveillance across the Greek economy, society, energy, tourism, housing, and finance.</div>',
        unsafe_allow_html=True,
    )

    all_kpis = get_overview_kpis(db_url, headline_only=False)

    # 1. Executive Metrics Strip
    active_count = sum(1 for k in all_kpis if k["has_data"])
    total_obs = sum(k["observation_count"] for k in all_kpis)
    latest_ref = max((k["latest_period"] for k in all_kpis if k["latest_period"] is not None), default="N/A")
    health_rate = round((active_count / len(all_kpis) * 100.0), 1) if all_kpis else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Catalog Indicators", f"{len(all_kpis)} Series", "6 Domains")
    m2.metric("Indicators with Data", f"{active_count} / {len(all_kpis)}", f"{health_rate}% stored")
    m3.metric("Stored Observations", f"{total_obs:,}", "Historical Records")
    m4.metric("Latest Reference Year", f"Ref: {latest_ref}", "Annual Series")

    st.markdown("---")

    # 2. Compact Controls Toolbar
    ctrl_col1, ctrl_col2 = st.columns([3, 3])
    with ctrl_col1:
        selected_topic = st.selectbox(
            "Domain Topic Filter",
            options=["All Topics"] + ALL_TOPICS,
            index=0,
        )
    with ctrl_col2:
        view_mode = st.radio(
            "View Format",
            options=["Headline Cards (9)", "All Indicators Grid (19)", "Compact Table"],
            horizontal=True,
            index=0,
        )

    # Filter KPIs
    target_kpis = all_kpis
    if view_mode == "Headline Cards (9)":
        target_kpis = [k for k in target_kpis if k.get("is_headline")]
    if selected_topic != "All Topics":
        target_kpis = [k for k in target_kpis if k["topic"] == selected_topic]

    # 3. KPI Display
    if view_mode == "Compact Table":
        table_rows = []
        for item in target_kpis:
            yoy_display = item["change_display"]
            table_rows.append(
                {
                    "Topic": f"{item['topic_icon']} {item['topic']}",
                    "Indicator": item["name"],
                    "Latest Value": item["formatted_value"],
                    "Reference Period": item["latest_period"] if item["latest_period"] else "—",
                    "YoY Change": yoy_display,
                    "Source Status": item["data_status"],
                    "Last Retrieved (UTC)": item["retrieved_at"] or "Never",
                    "Source": item["source_name"],
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, height=280)
    else:
        # Sleek 4-column Compact Card Grid
        for i in range(0, len(target_kpis), 4):
            cols = st.columns(4)
            for j in range(4):
                idx = i + j
                if idx < len(target_kpis):
                    item = target_kpis[idx]
                    val_str = item["formatted_value"]
                    p_str = f"Ref: {item['latest_period']}" if item["latest_period"] else "No Data"

                    yoy_str = item["change_display"]

                    topic_accent = {
                        "National Accounts & Output": "#38bdf8",
                        "Prices & Inflation": "#ec4899",
                        "Fiscal & Debt": "#f59e0b",
                        "Labor Market": "#10b981",
                        "External Sector & Trade": "#a855f7",
                        "Financial & Monetary": "#06b6d4",
                    }.get(item["topic"], "#0ea5e9")

                    status_badge = f'<span class="badge badge-info" style="font-size:0.65rem; padding:0.1rem 0.45rem;">{item["data_status"]}</span>'

                    cols[j].markdown(
                        f"""
                        <div class="card-kpi" style="border-left-color: {topic_accent};">
                            <div class="card-kpi-top">
                                <span class="card-kpi-topic" style="color: {topic_accent};">{item['topic_icon']} {item['topic']}</span>
                                {status_badge}
                            </div>
                            <div class="card-kpi-title" title="{item['name']}">{item['name']}</div>
                            <div class="card-kpi-val">{val_str}</div>
                            <div class="card-kpi-sub">
                                <span>{p_str}</span>
                                <span style="font-weight:600; color: #94a3b8">{yoy_str}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.markdown("---")

    # 4. What Changed: Top 3 Notable Shifts
    st.markdown("### ⚡ Notable Recent Movements")
    changes = get_what_changed_summary(db_url)
    if selected_topic != "All Topics":
        changes = [c for c in changes if c["topic"] == selected_topic]

    if changes:
        ch_cols = st.columns(min(3, len(changes)))
        for c_idx, ch in enumerate(changes[:3]):
            badge_cls = "badge-warn" if ch["badge"] == "WARN" else ("badge-info" if ch["badge"] == "INFO" else "badge-pass")
            ch_cols[c_idx].markdown(
                f"""
                <div class="callout-box" style="margin-bottom:0.4rem; padding: 0.65rem 0.9rem;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
                        <strong style="font-size:0.88rem;">{ch['topic_icon']} {ch['indicator']}</strong>
                        <span class="badge {badge_cls}">{ch['impact']}</span>
                    </div>
                    <div style="font-size:0.83rem; color:#cbd5e1; line-height:1.3;">{ch['narrative']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No significant period shifts detected.")

    st.markdown("---")

    # 5. Trend Trajectories: Clean 2-chart comparison per tab with fixed compact height (300px)
    st.markdown("### 📈 Domain Trend Trajectories")
    tab_econ, tab_soc, tab_tour, tab_energy, tab_fin = st.tabs([
        "🏛️ Economy & Debt",
        "👥 Society & Demographics",
        "🏖️ Tourism & Housing",
        "⚡ Energy & Emissions",
        "🏦 Sovereign Finance",
    ])

    with tab_econ:
        gdp_obs = get_latest_observations(db_url, "eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR")
        debt_obs = get_latest_observations(db_url, "eurostat.gov_10dd_edpt1.EL.PC_GDP.S13.GD")

        col_ec1, col_ec2 = st.columns(2)
        with col_ec1:
            if gdp_obs:
                df_gdp = pd.DataFrame([{"Year": o.period, "GDP (€M)": o.value} for o in gdp_obs if o.value is not None])
                fig_gdp = px.line(df_gdp, x="Year", y="GDP (€M)", title="Greek GDP at Current Market Prices (€M)", markers=True, color_discrete_sequence=["#38bdf8"])
                fig_gdp.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_gdp, use_container_width=True)
            else:
                st.info("No GDP data available.")
        with col_ec2:
            if debt_obs:
                df_debt = pd.DataFrame([{"Year": o.period, "Debt (% of GDP)": o.value} for o in debt_obs if o.value is not None])
                fig_debt = px.line(df_debt, x="Year", y="Debt (% of GDP)", title="General Government Gross Debt (% of GDP)", markers=True, color_discrete_sequence=["#fbbf24"])
                fig_debt.add_hline(y=60.0, line_dash="dash", line_color="#ef4444", annotation_text="Maastricht 60% Ceiling", annotation_position="bottom right")
                fig_debt.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_debt, use_container_width=True)
            else:
                st.info("No Debt data available.")

    with tab_soc:
        une_obs = get_latest_observations(db_url, "eurostat.une_rt_a.EL.Y15-74.PC_ACT.T")
        pop_obs = get_latest_observations(db_url, "eurostat.demo_pjan.EL.NR.TOTAL.T")

        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
            if une_obs:
                df_une = pd.DataFrame([{"Year": o.period, "Unemployment (%)": o.value} for o in une_obs if o.value is not None])
                fig_une = px.line(df_une, x="Year", y="Unemployment (%)", title="Unemployment Rate (Age 15–74, %)", markers=True, color_discrete_sequence=["#f87171"])
                fig_une.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_une, use_container_width=True)
            else:
                st.info("No unemployment data available.")
        with col_sc2:
            if pop_obs:
                df_pop = pd.DataFrame([{"Year": o.period, "Population": o.value} for o in pop_obs if o.value is not None])
                fig_pop = px.line(df_pop, x="Year", y="Population", title="Usually Resident Population (1 January)", markers=True, color_discrete_sequence=["#34d399"])
                fig_pop.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_pop, use_container_width=True)
            else:
                st.info("No population data available.")

    with tab_tour:
        tour_obs = get_latest_observations(db_url, "eurostat.tour_occ_arnat.EL.TOTAL.NR.I551-I553")
        hpi_obs = get_latest_observations(db_url, "eurostat.tipsho20.EL.I15_A_AVG")

        col_tr1, col_tr2 = st.columns(2)
        with col_tr1:
            if tour_obs:
                df_tour = pd.DataFrame([{"Year": o.period, "Arrivals": o.value} for o in tour_obs if o.value is not None])
                fig_tour = px.bar(df_tour, x="Year", y="Arrivals", title="Annual Tourist Arrivals (All Accommodation)", color_discrete_sequence=["#38bdf8"])
                fig_tour.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_tour, use_container_width=True)
            else:
                st.info("No tourism arrivals data available.")
        with col_tr2:
            if hpi_obs:
                df_hpi = pd.DataFrame([{"Year": o.period, "Index (2015=100)": o.value} for o in hpi_obs if o.value is not None])
                fig_hpi = px.line(df_hpi, x="Year", y="Index (2015=100)", title="House Price Index (Nominal, 2015=100)", markers=True, color_discrete_sequence=["#a855f7"])
                fig_hpi.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_hpi, use_container_width=True)
            else:
                st.info("No house price index data available.")

    with tab_energy:
        ren_obs = get_latest_observations(db_url, "eurostat.nrg_ind_ren.EL.REN.PC")
        ghg_obs = get_latest_observations(db_url, "eurostat.env_air_gge.EL.THS_T.GHG.TOTXMEMO")

        col_en1, col_en2 = st.columns(2)
        with col_en1:
            if ren_obs:
                df_ren = pd.DataFrame([{"Year": o.period, "Renewable Share (%)": o.value} for o in ren_obs if o.value is not None])
                fig_ren = px.line(df_ren, x="Year", y="Renewable Share (%)", title="Renewable Energy Share in Gross Final Consumption (%)", markers=True, color_discrete_sequence=["#10b981"])
                fig_ren.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_ren, use_container_width=True)
            else:
                st.info("No renewable energy data available.")
        with col_en2:
            if ghg_obs:
                df_ghg = pd.DataFrame([{"Year": o.period, "GHG Emissions (kt)": o.value} for o in ghg_obs if o.value is not None])
                fig_ghg = px.line(df_ghg, x="Year", y="GHG Emissions (kt)", title="Total Greenhouse Gas Emissions (kt CO2 eq)", markers=True, color_discrete_sequence=["#f43f5e"])
                fig_ghg.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_ghg, use_container_width=True)
            else:
                st.info("No greenhouse gas data available.")

    with tab_fin:
        bond_obs = get_latest_observations(db_url, "eurostat.irt_lt_mcby_a.EL.MCBY")
        debt_obs = get_latest_observations(db_url, "eurostat.gov_10dd_edpt1.EL.PC_GDP.S13.GD")

        col_fn1, col_fn2 = st.columns(2)
        with col_fn1:
            if bond_obs:
                df_bond = pd.DataFrame([{"Year": o.period, "10Y Yield (%)": o.value} for o in bond_obs if o.value is not None])
                fig_bond = px.line(df_bond, x="Year", y="10Y Yield (%)", title="Greece 10-Year Benchmark Sovereign Bond Yield (%)", markers=True, color_discrete_sequence=["#6366f1"])
                fig_bond.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_bond, use_container_width=True)
            else:
                st.info("No bond yield data available.")
        with col_fn2:
            if debt_obs:
                df_debt2 = pd.DataFrame([{"Year": o.period, "Debt (% of GDP)": o.value} for o in debt_obs if o.value is not None])
                fig_debt2 = px.bar(df_debt2, x="Year", y="Debt (% of GDP)", title="Sovereign Gross Debt Trajectory (% of GDP)", color_discrete_sequence=["#f59e0b"])
                fig_debt2.update_layout(template="plotly_dark", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_debt2, use_container_width=True)
            else:
                st.info("No debt data available.")


# ==============================================================================
# PAGE 2: 🔍 EXPLORE DATA
# ==============================================================================
elif page == "🔍 Explore Data":
    st.markdown('<div class="brand-title">🔍 Data Explorer & Indicator Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Browse, search, analyze, and export verified time-series data across all monitored Greek statistical domains. '
        'Compare indicators safely with unit scale validation.</div>',
        unsafe_allow_html=True,
    )

    # Filter Controls
    exp_filter_cols = st.columns([3, 2, 2])
    with exp_filter_cols[0]:
        search_query = st.text_input("🔎 Search Catalog", placeholder="e.g. inflation, debt, tourism, renewable, bond...").strip().lower()
    with exp_filter_cols[1]:
        topic_filter = st.selectbox("Topic", ["All Topics"] + ALL_TOPICS, index=0)
    with exp_filter_cols[2]:
        source_filter = st.selectbox("Source Authority", ["All Sources", "Eurostat", "ELSTAT", "Bank of Greece", "ECB"], index=0)

    # Filter Catalog Indicators
    matching_inds: list[IndicatorDefinition] = []
    for ind in INDICATOR_CATALOG:
        if topic_filter != "All Topics" and ind.topic != topic_filter:
            continue
        if source_filter != "All Sources" and source_filter.lower() not in ind.source_name.lower():
            continue
        if search_query:
            match_txt = f"{ind.name} {ind.description} {ind.dataset_code} {ind.topic} {ind.unit}".lower()
            if search_query not in match_txt:
                continue
        matching_inds.append(ind)

    if not matching_inds:
        st.warning("No indicators match your search and filter criteria.")
        st.stop()

    ind_select_map = {f"{ind.topic_icon} [{ind.topic}] {ind.name} ({ind.unit_short})": ind for ind in matching_inds}
    selected_label = st.selectbox("Select Active Indicator to Inspect", options=list(ind_select_map.keys()), index=0)
    current_ind = ind_select_map[selected_label]

    # Load Observations for Selected Indicator
    obs = get_latest_observations(db_url, current_ind.series_id)
    if not obs:
        st.info(f"No stored observations found for **{current_ind.name}**. Ingesting now...")
        with st.spinner("Fetching official Eurostat data..."):
            sync_result = sync_all_indicators(db_url, [current_ind], timeout=30)
            obs = get_latest_observations(db_url, current_ind.series_id)
            st.rerun()

    # KPI Summary Row for Selected Indicator
    valid_obs = [o for o in obs if o.value is not None]
    latest_val = valid_obs[-1].value if valid_obs else None
    latest_period = valid_obs[-1].period if valid_obs else "N/A"
    prev_val = valid_obs[-2].value if len(valid_obs) >= 2 else None

    annual_change = calculate_annual_change(
        valid_obs[-1] if valid_obs else None,
        valid_obs[-2] if len(valid_obs) >= 2 else None,
        current_ind.change_metric,
    )

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Latest Value", format_indicator_value(latest_val, current_ind.unit, current_ind.unit_short), annual_change["display"] + " YoY" if annual_change["value"] is not None else None, delta_color="off")
    kpi_cols[1].metric("Reference Period", str(latest_period), f"{len(valid_obs)} valid years")
    kpi_cols[2].metric("Measurement Unit", current_ind.unit_short, current_ind.frequency)
    kpi_cols[3].metric("Official Authority", current_ind.source_name, current_ind.dataset_code)

    latest_observation = valid_obs[-1] if valid_obs else None
    source_status = format_source_status(
        latest_observation.source_status if latest_observation else None,
        latest_observation is not None,
    )
    retrieved_at = latest_observation.retrieved_at if latest_observation else "Never"
    st.caption(
        f"Source status: {source_status}. Retrieved: {retrieved_at}. "
        "Annual changes require consecutive reference years."
    )
    st.markdown("---")

    # Time-series Chart & Controls
    st.markdown(f"### 📈 Time-Series: {current_ind.name}")
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        years = [o.period for o in obs]
        min_p, max_p = min(years) if years else 1995, max(years) if years else 2025
        chart_range = st.slider("Filter Period Range", min_value=min_p, max_value=max_p, value=(max(min_p, current_ind.start_year), max_p))
    with col_ctrl2:
        show_milestones = st.checkbox("Overlay Historical Milestones", value=True)

    df_obs = pd.DataFrame([
        {
            "Period": o.period,
            "Value": o.value,
            "Formatted": format_indicator_value(o.value, current_ind.unit, current_ind.unit_short),
            "Status": format_source_status(o.source_status, o.value is not None),
            "Raw": o.raw_value,
        }
        for o in obs
        if chart_range[0] <= o.period <= chart_range[1]
    ])

    if not df_obs.empty and df_obs["Value"].notnull().any():
        fig = px.line(
            df_obs,
            x="Period",
            y="Value",
            markers=True,
            title=f"{current_ind.name} ({current_ind.unit_short})",
            hover_data=["Formatted", "Status"],
            color_discrete_sequence=["#38bdf8"],
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0f172a",
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis_title=current_ind.unit_short,
            xaxis_title="Calendar Year",
        )

        if show_milestones:
            for ms in get_greek_economic_milestones():
                if chart_range[0] <= ms["year"] <= chart_range[1]:
                    fig.add_vline(
                        x=ms["year"],
                        line_width=1,
                        line_dash="dot",
                        line_color="#94a3b8",
                        annotation_text=ms.get("label", ms.get("title", "")),
                        annotation_position="top left",
                        annotation_font_size=10,
                        annotation_font_color="#94a3b8",
                    )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No numeric observations in selected period range.")

    # Data Table & Export CSV
    st.markdown("### 📋 Observations Data Table & Export")
    tbl_col1, tbl_col2 = st.columns([3, 1])
    with tbl_col2:
        csv_buffer = io.StringIO()
        df_export = df_obs[["Period", "Value", "Status", "Raw"]].copy()
        df_export["Indicator"] = current_ind.name
        df_export["Unit"] = current_ind.unit
        df_export["Source"] = current_ind.source_name
        df_export.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Export Observations as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"greek_data_{current_ind.indicator_id}_{chart_range[0]}_{chart_range[1]}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tbl_col1:
        st.dataframe(df_obs, use_container_width=True, height=220)

    st.markdown("---")

    # Safe Indicator Comparison Tool
    st.markdown("### ⚖️ Safe Indicator Comparison Tool")
    st.caption("Compare selected indicators only when units and frequencies make comparison meaningful. Incompatible raw scales are automatically normalized to protect statistical integrity.")

    cmp_cols = st.columns(2)
    with cmp_cols[0]:
        comp_ind_label_a = st.selectbox("Primary Indicator (A)", options=list(ind_select_map.keys()), index=0, key="cmp_a")
    with cmp_cols[1]:
        comp_ind_label_b = st.selectbox("Comparison Indicator (B)", options=list(ind_select_map.keys()), index=min(1, len(ind_select_map)-1), key="cmp_b")

    ind_a = ind_select_map[comp_ind_label_a]
    ind_b = ind_select_map[comp_ind_label_b]

    obs_a_raw = get_latest_observations(db_url, ind_a.series_id)
    obs_b_raw = get_latest_observations(db_url, ind_b.series_id)

    cmp_result = calculate_safe_comparison(
        [{"period": o.period, "value": o.value} for o in obs_a_raw],
        {"name": ind_a.name, "unit": ind_a.unit, "unit_short": ind_a.unit_short},
        [{"period": o.period, "value": o.value} for o in obs_b_raw],
        {"name": ind_b.name, "unit": ind_b.unit, "unit_short": ind_b.unit_short},
    )

    if cmp_result.get("indexing_disabled"):
        st.error(f"🚫 {cmp_result.get('message')}")
        if cmp_result.get("error_explanation"):
            st.caption(f"**Baseline Issue**: {cmp_result['error_explanation']}")
    elif cmp_result.get("data"):
        df_cmp = pd.DataFrame(cmp_result["data"])
        if cmp_result["compatible_raw"]:
            st.success(f"✅ {cmp_result['message']}")
            fig_cmp = go.Figure()
            fig_cmp.add_trace(go.Scatter(x=df_cmp["period"], y=df_cmp["raw_a"], mode="lines+markers", name=f"{ind_a.name} ({ind_a.unit_short})", line=dict(color="#38bdf8")))
            fig_cmp.add_trace(go.Scatter(x=df_cmp["period"], y=df_cmp["raw_b"], mode="lines+markers", name=f"{ind_b.name} ({ind_b.unit_short})", line=dict(color="#fbbf24")))
            fig_cmp.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", yaxis_title=ind_a.unit_short, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_cmp, use_container_width=True)
        else:
            st.warning(f"⚠️ {cmp_result['message']}")
            fig_cmp = go.Figure()
            fig_cmp.add_trace(go.Scatter(x=df_cmp["period"], y=df_cmp["index_a"], mode="lines+markers", name=f"{ind_a.name} (Re-indexed: {cmp_result['base_period']}=100)", line=dict(color="#38bdf8")))
            fig_cmp.add_trace(go.Scatter(x=df_cmp["period"], y=df_cmp["index_b"], mode="lines+markers", name=f"{ind_b.name} (Re-indexed: {cmp_result['base_period']}=100)", line=dict(color="#fbbf24")))
            fig_cmp.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", yaxis_title="Indexed Trajectory (Base=100)", margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_cmp, use_container_width=True)
    else:
        st.info(cmp_result.get("message", "No comparison data available."))


# ==============================================================================
# PAGE 3: 🇪🇺 GREECE IN CONTEXT
# ==============================================================================
elif page == "🇪🇺 Greece in Context":
    st.markdown('<div class="brand-title">🇪🇺 Greece in Context: International Benchmarks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Benchmark Greece against the EU-27 European Union average and peer Mediterranean and European economies '
        '(Germany, Italy, Spain, Portugal, Cyprus) using harmonized official Eurostat series.</div>',
        unsafe_allow_html=True,
    )

    # Comparable Indicator Selector
    comparable_inds = [ind for ind in INDICATOR_CATALOG if ind.comparable_eu and ind.context_series_key]
    cmp_ind_map = {f"{ind.topic_icon} {ind.name} ({ind.unit_short})": ind for ind in comparable_inds}

    bench_cols = st.columns([3, 2])
    with bench_cols[0]:
        selected_bench_label = st.selectbox("Select Benchmark Indicator", options=list(cmp_ind_map.keys()), index=0)
        active_bench_ind = cmp_ind_map[selected_bench_label]
    with bench_cols[1]:
        bench_year_range = st.slider("Time Period", min_value=2000, max_value=2025, value=(2008, 2025), key="bench_slider")

    # Load Stored Country Benchmarks
    benchmarks_data = get_country_benchmarks(db_url, active_bench_ind.indicator_id)
    if not benchmarks_data:
        st.info(f"Fetching official multi-country benchmarks from Eurostat for {active_bench_ind.name}...")
        with st.spinner("Connecting to Eurostat SDMX Dissemination API..."):
            fetched_b = fetch_indicator_benchmarks(active_bench_ind, timeout=30)
            if fetched_b:
                save_country_benchmarks(db_url, active_bench_ind.indicator_id, fetched_b)
                benchmarks_data = get_country_benchmarks(db_url, active_bench_ind.indicator_id)
                st.rerun()
            else:
                st.warning("No benchmark data returned from Eurostat.")
                st.stop()

    df_bench = pd.DataFrame(benchmarks_data)
    df_bench = df_bench[(df_bench["period"] >= bench_year_range[0]) & (df_bench["period"] <= bench_year_range[1])]

    # Country Filter Selector
    all_countries = sorted(df_bench["country_code"].unique())
    country_display_map = {c: f"{COUNTRY_FLAGS.get(c, '')} {COUNTRY_NAMES.get(c, c)}" for c in all_countries}

    selected_countries = st.multiselect(
        "Select Economies to Compare",
        options=all_countries,
        default=all_countries,
        format_func=lambda c: country_display_map.get(c, c),
    )

    df_filtered_bench = df_bench[df_bench["country_code"].isin(selected_countries)]

    # 1. Latest Common Reference Period Bar Chart
    latest_common_period = df_filtered_bench[df_filtered_bench["value"].notnull()]["period"].max()
    df_latest_bar = df_filtered_bench[df_filtered_bench["period"] == latest_common_period].copy()
    df_latest_bar = df_latest_bar.sort_values(by="value", ascending=True)

    st.markdown(f"### 📊 Benchmark Standings ({latest_common_period})")
    if not df_latest_bar.empty and df_latest_bar["value"].notnull().any():
        # Distinguish Greece with unique color
        df_latest_bar["Color"] = df_latest_bar["country_code"].apply(lambda c: "#38bdf8" if c == "EL" else ("#fbbf24" if c == "EU27_2020" else "#64748b"))
        df_latest_bar["Label"] = df_latest_bar["country_code"].apply(lambda c: country_display_map.get(c, c))

        fig_bar = px.bar(
            df_latest_bar,
            x="value",
            y="Label",
            orientation="h",
            title=f"{active_bench_ind.name} — Year {latest_common_period} ({active_bench_ind.unit_short})",
            color="country_code",
            color_discrete_map={"EL": "#38bdf8", "EU27_2020": "#fbbf24", "DE": "#64748b", "IT": "#94a3b8", "ES": "#cbd5e1", "PT": "#475569", "CY": "#0284c7"},
        )
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0f172a",
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title=active_bench_ind.unit_short,
            yaxis_title=None,
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No comparative values found for the latest reference year.")

    # 2. Historical Comparative Time Series
    st.markdown("### 📈 Historical Multi-Country Trajectory")
    if not df_filtered_bench.empty:
        df_filtered_bench["DisplayCountry"] = df_filtered_bench["country_code"].apply(lambda c: country_display_map.get(c, c))
        fig_multi = px.line(
            df_filtered_bench,
            x="period",
            y="value",
            color="DisplayCountry",
            markers=True,
            title=f"Evolution of {active_bench_ind.name} across European Peers ({active_bench_ind.unit_short})",
            color_discrete_map={
                country_display_map.get("EL", "EL"): "#38bdf8",
                country_display_map.get("EU27_2020", "EU27_2020"): "#fbbf24",
            },
        )
        fig_multi.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0f172a",
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="Calendar Year",
            yaxis_title=active_bench_ind.unit_short,
        )
        st.plotly_chart(fig_multi, use_container_width=True)

    # 3. Disclosures & Full Comparative Matrix
    st.markdown("### 📋 Comparative Observations Matrix & Disclosures")
    st.caption("Harmonized ESA 2010 / LFS / MIP series from Eurostat. Missing observations are documented transparently.")
    pivot_df = df_filtered_bench.pivot(index="period", columns="country_code", values="value").sort_index(ascending=False)
    st.dataframe(pivot_df, use_container_width=True, height=220)


# ==============================================================================
# PAGE 4: 🏛️ FISCAL & DEBT SURVEILLANCE
# ==============================================================================
elif page == "🏛️ Fiscal & Debt Surveillance":
    st.markdown('<div class="brand-title">🏛️ Sovereign Debt & Fiscal Surveillance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Specialized surveillance of Greece\'s sovereign debt trajectory, post-pandemic deleveraging dynamics, '
        'European fiscal governance rules (Maastricht criteria), and sovereign bond yield normalization.</div>',
        unsafe_allow_html=True,
    )

    debt_series_id = "eurostat.gov_10dd_edpt1.EL.PC_GDP.S13.GD"
    gdp_series_id = "eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR"
    bond_series_id = "eurostat.irt_lt_mcby_a.EL.MCBY"

    debt_obs = get_latest_observations(db_url, debt_series_id)
    gdp_obs = get_latest_observations(db_url, gdp_series_id)
    bond_obs = get_latest_observations(db_url, bond_series_id)

    valid_debt = [o for o in debt_obs if o.value is not None]
    valid_bond = [o for o in bond_obs if o.value is not None]

    latest_debt = valid_debt[-1] if valid_debt else None
    prev_debt = valid_debt[-2] if len(valid_debt) >= 2 else None
    peak_debt = max(valid_debt, key=lambda o: o.value) if valid_debt else None
    latest_bond = valid_bond[-1] if valid_bond else None

    # Fiscal Headline Cards
    debt_val_str = f"{latest_debt.value:.1f}%" if latest_debt and latest_debt.value is not None else "N/A"
    debt_diff = round(latest_debt.value - prev_debt.value, 1) if latest_debt and prev_debt and latest_debt.value is not None and prev_debt.value is not None else None
    deleveraging_str = f"{debt_diff:+.1f} pp YoY" if debt_diff is not None else "N/A"

    peak_drop = round(latest_debt.value - peak_debt.value, 1) if latest_debt and peak_debt and latest_debt.value is not None and peak_debt.value is not None else None
    drop_str = f"{peak_drop:+.1f} pp from peak ({peak_debt.period})" if peak_drop is not None and peak_debt else "N/A"

    bond_val_str = f"{latest_bond.value:.2f}%" if latest_bond and latest_bond.value is not None else "N/A"
    bond_period_str = f"Ref: {latest_bond.period}" if latest_bond else "N/A"

    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.1rem;">
            <div class="card-kpi" style="border-left-color: #f59e0b;">
                <div class="card-kpi-top">
                    <span class="card-kpi-topic" style="color: #f59e0b;">🏛️ FISCAL & DEBT</span>
                </div>
                <div class="card-kpi-title" title="Sovereign Debt Ratio">Sovereign Debt Ratio</div>
                <div class="card-kpi-val" style="color: #fbbf24;">{debt_val_str}</div>
                <div class="card-kpi-sub">
                    <span>Ref: {latest_debt.period if latest_debt else 'N/A'}</span>
                    <span style="color: #34d399; font-weight:600;">{deleveraging_str}</span>
                </div>
            </div>
            <div class="card-kpi" style="border-left-color: #10b981;">
                <div class="card-kpi-top">
                    <span class="card-kpi-topic" style="color: #10b981;">📉 DELEVERAGING</span>
                </div>
                <div class="card-kpi-title" title="Deleveraging From Peak">Deleveraging vs Peak</div>
                <div class="card-kpi-val" style="color: #34d399;">{drop_str}</div>
                <div class="card-kpi-sub">
                    <span>Peak: {peak_debt.value if peak_debt else 'N/A'}%</span>
                </div>
            </div>
            <div class="card-kpi" style="border-left-color: #38bdf8;">
                <div class="card-kpi-top">
                    <span class="card-kpi-topic" style="color: #38bdf8;">📊 BOND YIELD</span>
                </div>
                <div class="card-kpi-title" title="10Y Sovereign Yield">10Y Benchmark Yield</div>
                <div class="card-kpi-val" style="color: #38bdf8;">{bond_val_str}</div>
                <div class="card-kpi-sub">
                    <span>{bond_period_str}</span>
                    <span style="color: #94a3b8;">Market Pricing</span>
                </div>
            </div>
            <div class="card-kpi" style="border-left-color: #f87171;">
                <div class="card-kpi-top">
                    <span class="card-kpi-topic" style="color: #f87171;">🎯 MAASTRICHT 60%</span>
                </div>
                <div class="card-kpi-title" title="Maastricht Benchmark Gap">Target Debt Gap</div>
                <div class="card-kpi-val" style="color: #f87171;">{debt_val_str}</div>
                <div class="card-kpi-sub">
                    <span>Target: 60% of GDP</span>
                    <span style="color: #f87171; font-weight: 600;">Excess Gap</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Historical Debt Chart with Milestones
    st.markdown("### 📈 Sovereign Debt-to-GDP Trajectory & Historical Crisis Milestones")
    st.caption("Official general government gross consolidated debt as a percentage of GDP (Eurostat table `gov_10dd_edpt1`, ESA 2010).")

    if valid_debt:
        df_fiscal = pd.DataFrame([{"Year": o.period, "Debt (% of GDP)": o.value} for o in valid_debt])
        fig_fiscal = px.line(
            df_fiscal,
            x="Year",
            y="Debt (% of GDP)",
            title="Greece General Government Gross Debt (% of GDP, 1995–Present)",
            markers=True,
            color_discrete_sequence=["#fbbf24"],
        )
        fig_fiscal.add_hline(
            y=60.0,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text="Maastricht Treaty 60% Benchmark Ceiling",
            annotation_position="bottom right",
        )

        # Annotate Greek economic milestones
        milestones = get_greek_economic_milestones()
        debt_years = {o.period: o.value for o in valid_debt}
        for m in milestones:
            m_yr = m["year"]
            if m_yr in debt_years:
                fig_fiscal.add_annotation(
                    x=m_yr,
                    y=debt_years[m_yr],
                    text=f"<b>{m['year']}</b>: {m.get('label', m.get('event', ''))}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1.5,
                    arrowcolor="#38bdf8",
                    ax=0,
                    ay=-45 if m_yr % 2 == 0 else 45,
                    bgcolor="rgba(15, 23, 42, 0.85)",
                    bordercolor="#38bdf8",
                    borderwidth=1,
                    borderpad=3,
                    font=dict(size=9, color="#f1f5f9"),
                )

        fig_fiscal.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0f172a",
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis_title="Debt (% of GDP)",
            xaxis_title="Year",
        )
        st.plotly_chart(fig_fiscal, use_container_width=True)
    else:
        st.info("No debt data currently available in the database.")

    # Two column deep-dive: Snowball effect & Bond yields
    col_sn, col_by = st.columns(2)
    with col_sn:
        st.markdown("### ❄️ Macroeconomic Denominator & Snowball Dynamics")
        latest_debt_yr = latest_debt.period if latest_debt else 2025
        st.markdown(
            f"A country's sovereign debt-to-GDP ratio $D/Y$ declines when nominal economic output $Y$ grows faster than debt stock $D$. "
            f"Greece achieved the **fastest debt ratio reduction in the EU** between 2020 and {latest_debt_yr} through rapid nominal GDP growth combined with primary fiscal surpluses."
        )
        if valid_debt and gdp_obs:
            dict_debt = {o.period: o.value for o in valid_debt}
            dict_gdp = {o.period: o.value for o in gdp_obs if o.value is not None}
            common_yrs = sorted(set(dict_debt.keys()) & set(dict_gdp.keys()))

            snow_rows = []
            for y_idx in range(1, len(common_yrs)):
                curr_y = common_yrs[y_idx]
                prev_y = common_yrs[y_idx - 1]
                gdp_g = ((dict_gdp[curr_y] - dict_gdp[prev_y]) / dict_gdp[prev_y]) * 100.0
                debt_delta = dict_debt[curr_y] - dict_debt[prev_y]
                snow_rows.append({"Year": curr_y, "Nominal GDP Growth (%)": round(gdp_g, 2), "Debt Ratio Change (pp)": round(debt_delta, 2)})

            if snow_rows:
                df_snow = pd.DataFrame(snow_rows)
                fig_snow = px.bar(
                    df_snow[df_snow["Year"] >= 2010],
                    x="Year",
                    y=["Nominal GDP Growth (%)", "Debt Ratio Change (pp)"],
                    barmode="group",
                    title="Nominal GDP Growth vs Debt Ratio Annual Shift (Post-2010)",
                    color_discrete_map={"Nominal GDP Growth (%)": "#34d399", "Debt Ratio Change (pp)": "#f87171"},
                )
                fig_snow.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_snow, use_container_width=True)

    with col_by:
        st.markdown("### 📉 10-Year Sovereign Benchmark Yield Normalization")
        st.markdown(
            "The long-term sovereign bond yield reflects market perception of Greek sovereign creditworthiness. "
            "From crisis peaks (>25%), Greek yields returned to investment-grade pricing, trading on par with southern European peers."
        )
        if valid_bond:
            df_b = pd.DataFrame([{"Year": o.period, "10Y Yield (%)": o.value} for o in valid_bond])
            fig_b = px.line(
                df_b,
                x="Year",
                y="10Y Yield (%)",
                title="Greece 10-Year Benchmark Sovereign Bond Yield (1995–Present)",
                markers=True,
                color_discrete_sequence=["#38bdf8"],
            )
            fig_b.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_b, use_container_width=True)
        else:
            st.info("No bond yield data available.")

    # European Fiscal Governance Rules Framework
    st.markdown("---")
    st.markdown("### ⚖️ European Fiscal Governance & Surveillance Rulebook")
    st.markdown(
        """
        Under the **Stability and Growth Pact (SGP)** and post-programme surveillance commitments:
        - **Maastricht Debt Ceiling (60% of GDP):** General government debt must remain below 60% of GDP or diminish sufficiently toward it at a satisfactory pace.
        - **Maastricht Deficit Ceiling (3% of GDP):** Net general government borrowing must not exceed 3% of GDP.
        - **Post-Programme Commitments:** Enhanced post-program monitoring reports by the European Commission verify Greek debt sustainability and primary fiscal balance targets.
        """
    )


# ==============================================================================
# PAGE 5: 🔬 CROSS-SERIES ANALYSIS & LAB
# ==============================================================================
elif page == "🔬 Cross-Series Analysis & Lab":
    st.markdown('<div class="brand-title">🔬 Cross-Series Analysis & Macroeconomic Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Empirical correlation matrices, bivariate regression modeling, and unit-scale normalized comparisons across official Greek time-series.</div>',
        unsafe_allow_html=True,
    )

    tab_lab_corr, tab_lab_scatter, tab_lab_safe = st.tabs([
        "🔥 Correlation Heatmap Matrix",
        "📐 Bivariate Scatter & Trendline",
        "⚖️ Safe Unit-Scale Comparison Lab",
    ])

    with tab_lab_corr:
        st.markdown("### 🧮 Multi-Indicator Pearson Correlation Matrix")
        st.caption("Measures linear co-movement between official Greek indicators across overlapping annual observation periods (min 5 periods).")

        corr_res = calculate_indicator_correlation_matrix(db_url, min_periods=5)
        if corr_res.get("correlation_matrix"):
            corr_df = pd.DataFrame(
                corr_res["correlation_matrix"],
                index=corr_res["labels"],
                columns=corr_res["labels"],
            )
            fig_heatmap = px.imshow(
                corr_df,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1.0,
                zmax=1.0,
                title=f"Pairwise Pearson Correlation Matrix ({corr_res['common_periods_count']} overlapping observations)",
            )
            fig_heatmap.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#0f172a",
                margin=dict(l=10, r=10, t=40, b=10),
                height=520,
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Insufficient overlapping observations across indicators to construct correlation matrix. Sync all indicators first.")

    with tab_lab_scatter:
        st.markdown("### 📐 Bivariate Regression & Scatter Plot")
        st.caption("Inspect relationships between any two public metrics (e.g. Okun's Law: GDP vs Unemployment; Phillips Curve: Inflation vs Unemployment).")

        biv_cols = st.columns(2)
        catalog_names = {f"{ind.topic_icon} {ind.name}": ind for ind in INDICATOR_CATALOG}
        with biv_cols[0]:
            sel_x_name = st.selectbox("Select Independent Variable (X-axis)", options=list(catalog_names.keys()), index=0)
        with biv_cols[1]:
            sel_y_name = st.selectbox("Select Dependent Variable (Y-axis)", options=list(catalog_names.keys()), index=1)

        ind_x = catalog_names[sel_x_name]
        ind_y = catalog_names[sel_y_name]

        obs_x = get_latest_observations(db_url, ind_x.series_id)
        obs_y = get_latest_observations(db_url, ind_y.series_id)

        dict_x = {o.period: o.value for o in obs_x if o.value is not None}
        dict_y = {o.period: o.value for o in obs_y if o.value is not None}
        common_p = sorted(set(dict_x.keys()) & set(dict_y.keys()))

        if len(common_p) >= 3:
            df_biv = pd.DataFrame([{"Year": p, ind_x.name: dict_x[p], ind_y.name: dict_y[p]} for p in common_p])
            fig_scatter = px.scatter(
                df_biv,
                x=ind_x.name,
                y=ind_y.name,
                text="Year",
                trendline="ols",
                title=f"{ind_x.name} vs. {ind_y.name} ({len(common_p)} Overlapping Years)",
                color_discrete_sequence=["#38bdf8"],
            )
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#0f172a",
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis_title=f"{ind_x.name} ({ind_x.unit_short})",
                yaxis_title=f"{ind_y.name} ({ind_y.unit_short})",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Correlation coefficient
            import numpy as np
            corr_val = float(np.corrcoef(df_biv[ind_x.name], df_biv[ind_y.name])[0, 1])
            r_squared = corr_val ** 2
            st.markdown(
                f"""
                <div class="callout-box">
                    <strong>Statistical Fit:</strong> Pearson Correlation $r = {corr_val:.3f}$ •
                    Coefficient of Determination $R^2 = {r_squared:.3f}$ ({r_squared * 100:.1f}% of variance explained).<br>
                    <strong>Direction:</strong> {'Positive Co-movement (variables move in the same direction)' if corr_val > 0 else 'Negative Inverse Relationship (variables move oppositely)'}.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Less than 3 overlapping periods found between the selected indicators.")

    with tab_lab_safe:
        st.markdown("### ⚖️ Safe Unit-Scale Comparison Lab")
        st.caption("Automatically detects unit compatibility and prevents misleading raw comparisons by re-indexing differing scales to Base Year = 100.")

        cmp_cols = st.columns(2)
        with cmp_cols[0]:
            sel_safe_a = st.selectbox("Select Series A", options=list(catalog_names.keys()), index=0, key="lab_safe_a")
        with cmp_cols[1]:
            sel_safe_b = st.selectbox("Select Series B", options=list(catalog_names.keys()), index=2 if len(catalog_names) > 2 else 1, key="lab_safe_b")

        ind_s_a = catalog_names[sel_safe_a]
        ind_s_b = catalog_names[sel_safe_b]

        obs_s_a = [{"period": o.period, "value": o.value} for o in get_latest_observations(db_url, ind_s_a.series_id)]
        obs_s_b = [{"period": o.period, "value": o.value} for o in get_latest_observations(db_url, ind_s_b.series_id)]

        meta_s_a = {"name": ind_s_a.name, "unit": ind_s_a.unit, "unit_short": ind_s_a.unit_short}
        meta_s_b = {"name": ind_s_b.name, "unit": ind_s_b.unit, "unit_short": ind_s_b.unit_short}

        res_safe = calculate_safe_comparison(obs_s_a, meta_s_a, obs_s_b, meta_s_b)
        if res_safe.get("indexing_disabled"):
            st.error(f"🚫 {res_safe.get('message')}")
            if res_safe.get("error_explanation"):
                st.caption(f"**Baseline Issue**: {res_safe['error_explanation']}")
        elif res_safe.get("data"):
            df_safe = pd.DataFrame(res_safe["data"])
            if res_safe["compatible_raw"]:
                st.success(f"✅ {res_safe['message']}")
                fig_s = go.Figure()
                fig_s.add_trace(go.Scatter(x=df_safe["period"], y=df_safe["raw_a"], mode="lines+markers", name=f"{ind_s_a.name} ({ind_s_a.unit_short})", line=dict(color="#38bdf8")))
                fig_s.add_trace(go.Scatter(x=df_safe["period"], y=df_safe["raw_b"], mode="lines+markers", name=f"{ind_s_b.name} ({ind_s_b.unit_short})", line=dict(color="#fbbf24")))
                fig_s.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", yaxis_title=ind_s_a.unit_short, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_s, use_container_width=True)
            else:
                st.warning(f"⚠️ {res_safe['message']}")
                fig_s = go.Figure()
                fig_s.add_trace(go.Scatter(x=df_safe["period"], y=df_safe["index_a"], mode="lines+markers", name=f"{ind_s_a.name} (Base {res_safe['base_period']}=100)", line=dict(color="#38bdf8")))
                fig_s.add_trace(go.Scatter(x=df_safe["period"], y=df_safe["index_b"], mode="lines+markers", name=f"{ind_s_b.name} (Base {res_safe['base_period']}=100)", line=dict(color="#fbbf24")))
                fig_s.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a", yaxis_title="Indexed Value (Base=100)", margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.info(res_safe.get("message", "No overlapping data available."))


# ==============================================================================
# PAGE 6: 🛡️ DATA QUALITY & FRESHNESS
# ==============================================================================
elif page == "🛡️ Data Quality & Freshness":
    st.markdown('<div class="brand-title">🛡️ Data Quality & Freshness Surveillance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Independent verification of completeness, timeliness, historical revisions, and anomaly detection. '
        'Separated quality findings from country statistics to ensure complete auditing transparency.</div>',
        unsafe_allow_html=True,
    )

    # Cross-Indicator Quality & Freshness Health Matrix
    st.markdown("### 📡 Source Checks & Retrieval Age")
    st.caption("Retrieval age describes when this app checked the source. The reference year and source flags describe the observations; a recent check does not make a value final or current-year data.")
    all_status = get_all_series_status(db_url)

    status_rows = []
    for ind in INDICATOR_CATALOG:
        st_entry = all_status.get(ind.series_id)
        if st_entry:
            run_status = st_entry["status"]
            latest_p = st_entry["latest_period"]
            checked_at = st_entry["checked_at"][:19].replace("T", " ") if st_entry["checked_at"] else "N/A"
            errs = st_entry["error_count"]
            warns = st_entry["warning_count"]
            freshness = format_check_age(st_entry["checked_at"])
        else:
            run_status = "NOT_SYNCED"
            latest_p = "—"
            checked_at = "Never"
            errs = 0
            warns = 0
            freshness = "Not checked"

        status_rows.append({
            "Topic": f"{ind.topic_icon} {ind.topic}",
            "Indicator": ind.name,
            "Latest Period": latest_p,
            "Retrieval Age": freshness,
            "Audit Status": run_status,
            "Errors": errs,
            "Warnings": warns,
            "Last Checked (UTC)": checked_at,
            "series_id": ind.series_id,
        })

    df_status = pd.DataFrame(status_rows)
    st.dataframe(
        df_status[["Topic", "Indicator", "Latest Period", "Retrieval Age", "Audit Status", "Errors", "Warnings", "Last Checked (UTC)"]],
        use_container_width=True,
        height=280,
    )

    st.markdown("---")

    # Deep-Dive Quality Audit for Selected Series
    st.markdown("### 🔬 In-Depth Quality Audit & Scorecard")
    series_select_opts = {f"{ind.topic_icon} {ind.name}": ind for ind in INDICATOR_CATALOG if ind.series_id in all_status}
    if not series_select_opts:
        st.info("Sync indicators first to view in-depth scorecards.")
        st.stop()

    audit_label = st.selectbox("Select Series to Audit", options=list(series_select_opts.keys()), index=0)
    audit_ind = series_select_opts[audit_label]

    runs = list_runs(db_url, limit=20, series_id=audit_ind.series_id)
    if not runs:
        st.warning("No runs found for this series.")
        st.stop()

    latest_run = runs[0]
    run_details = get_run_details(db_url, latest_run["id"])
    if not run_details:
        st.error("Could not load run details.")
        st.stop()

    findings = run_details["findings"]
    obs_list = run_details["observations"]
    known_gaps = getattr(audit_ind, "known_missing_periods", {})
    scorecard = calculate_quality_scorecard(obs_list, findings, audit_ind.start_year, known_missing_periods=known_gaps)

    # Scorecard Box
    st.markdown(
        f"""
        <div class="scorecard-box">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="margin:0; font-size:1.4rem;">Quality Score: {scorecard['overall_score']}/100</h3>
                    <span style="color:#94a3b8; font-size:0.85rem;">Project-defined rule score; does not certify accuracy or finality</span>
                </div>
                <div>
                    <span class="badge {'badge-error' if scorecard['error_count'] or scorecard['grade'] == 'F' else 'badge-warn' if scorecard['warning_count'] else 'badge-pass'}" style="font-size:1.2rem; padding:0.4rem 1rem;">Grade: {scorecard['grade']}</span>
                </div>
            </div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem; margin-top:1.2rem;">
                <div style="background:#0f172a; padding:0.75rem; border-radius:0.5rem; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.78rem;">COMPLETENESS</div>
                    <div style="font-size:1.3rem; font-weight:700; color:#38bdf8;">{scorecard['completeness_score']}%</div>
                </div>
                <div style="background:#0f172a; padding:0.75rem; border-radius:0.5rem; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.78rem;">PERIOD VALIDITY</div>
                    <div style="font-size:1.3rem; font-weight:700; color:#34d399;">{scorecard['validity_score']}%</div>
                </div>
                <div style="background:#0f172a; padding:0.75rem; border-radius:0.5rem; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.78rem;">UNIQUENESS</div>
                    <div style="font-size:1.3rem; font-weight:700; color:#34d399;">{scorecard['uniqueness_score']}%</div>
                </div>
                <div style="background:#0f172a; padding:0.75rem; border-radius:0.5rem; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.78rem;">PLAUSIBILITY</div>
                    <div style="font-size:1.3rem; font-weight:700; color:#fbbf24;">{scorecard['plausibility_score']}%</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Historical Revisions Audit
    if len(runs) >= 2:
        st.markdown("### 🔄 Historical Revision Detection between Runs")
        prev_run = runs[1]
        prev_details = get_run_details(db_url, prev_run["id"])
        if prev_details:
            diff_res = compare_run_snapshots(prev_details["observations"], run_details["observations"])
            if diff_res["has_changes"]:
                st.warning(f"Detected {diff_res['revised_count']} revised historical observation(s) between Run #{prev_run['id']} and Run #{latest_run['id']}!")
                st.dataframe(pd.DataFrame(diff_res["diffs"]), use_container_width=True)
            else:
                st.success("✅ Zero retrospective revisions detected across historical observations between consecutive ingestion runs.")

    # Quality Findings Table & Guidance
    st.markdown("### 📋 Quality Findings Audit Log")
    st.info("💡 **Methodology Guidance:** Warnings indicate unusual volatility or data revisions that warrant review. A warning is a reason to inspect data, NOT definitive proof that official statistics are incorrect.")

    rule_descs = get_quality_rule_descriptions()
    findings_data = []
    for f in findings:
        r_info = rule_descs.get(f["rule"], {})
        findings_data.append({
            "Severity": f["severity"],
            "Rule Code": f["rule"],
            "Rule Name": r_info.get("name", f["rule"]),
            "Period": str(f["period"]) if f["period"] is not None else "All",
            "Message": f["message"],
            "Review Guidance": r_info.get("review_guidance", "Inspect source release notes."),
        })

    st.dataframe(pd.DataFrame(findings_data), use_container_width=True)

    # Download Audit Report Button
    st.markdown("### 📄 Download Formal Quality Audit Report")
    audit_report_md = generate_markdown_audit_report(latest_run, findings, scorecard, audit_ind.name, indicator=audit_ind)
    st.download_button(
        "📥 Download Markdown Audit Report",
        data=audit_report_md,
        file_name=f"audit_report_{audit_ind.indicator_id}_run_{latest_run['id']}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ==============================================================================
# PAGE 7: 📑 AUDIT REPORTS & DATA EXPORT
# ==============================================================================
elif page == "📑 Audit Reports & Data Export":
    st.markdown('<div class="brand-title">📑 Audit Reports & Data Export Center</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Download machine-readable public datasets, generate statistical quality reports, '
        'and inspect retroactive data revisions between official ingestion runs.</div>',
        unsafe_allow_html=True,
    )

    tab_exp_data, tab_exp_rep, tab_exp_diff, tab_exp_api = st.tabs([
        "📥 Data Export Center",
        "📄 Formal Audit Report Generator",
        "🔄 Historical Revision Inspector",
        "🔗 Developer & Researcher Wire API",
    ])

    with tab_exp_data:
        st.markdown("### 📥 Machine-Readable Data Export")
        st.caption("Export official time-series observations in CSV or JSON formats for downstream econometric modeling, policy research, or auditing.")

        exp_mode = st.radio(
            "Export Scope",
            options=["All 19 Indicators Consolidated", "Single Selected Indicator"],
            horizontal=True,
            index=0,
        )

        catalog_by_name = {f"{ind.topic_icon} {ind.name}": ind for ind in INDICATOR_CATALOG}

        if exp_mode == "Single Selected Indicator":
            sel_exp_name = st.selectbox("Select Indicator to Export", options=list(catalog_by_name.keys()), index=0)
            ind_to_exp = catalog_by_name[sel_exp_name]
            obs_to_exp = get_latest_observations(db_url, ind_to_exp.series_id)

            rows_exp = [
                {
                    "indicator_id": ind_to_exp.indicator_id,
                    "indicator_name": ind_to_exp.name,
                    "topic": ind_to_exp.topic,
                    "unit": ind_to_exp.unit,
                    "period": o.period,
                    "value": o.value,
                    "source_status": o.source_status,
                    "source_name": ind_to_exp.source_name,
                    "dataset_code": ind_to_exp.dataset_code,
                    "retrieved_at": o.retrieved_at,
                }
                for o in obs_to_exp
            ]
            df_export = pd.DataFrame(rows_exp)
            file_base = f"greek_data_{ind_to_exp.indicator_id}"
        else:
            all_rows = []
            for ind_item in INDICATOR_CATALOG:
                obs_list = get_latest_observations(db_url, ind_item.series_id)
                for o in obs_list:
                    all_rows.append(
                        {
                            "indicator_id": ind_item.indicator_id,
                            "indicator_name": ind_item.name,
                            "topic": ind_item.topic,
                            "unit": ind_item.unit,
                            "period": o.period,
                            "value": o.value,
                            "source_status": o.source_status,
                            "source_name": ind_item.source_name,
                            "dataset_code": ind_item.dataset_code,
                            "retrieved_at": o.retrieved_at,
                        }
                    )
            df_export = pd.DataFrame(all_rows)
            file_base = "greek_public_data_all_indicators"

        st.markdown(f"**Records Prepared:** `{len(df_export)}` rows")

        dl_cols = st.columns(2)
        with dl_cols[0]:
            csv_data = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV Dataset",
                data=csv_data,
                file_name=f"{file_base}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
        with dl_cols[1]:
            json_data = df_export.to_json(orient="records", indent=2).encode("utf-8")
            st.download_button(
                "📥 Download JSON Dataset",
                data=json_data,
                file_name=f"{file_base}.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("#### Preview Data")
        st.dataframe(df_export, use_container_width=True, height=260)

    with tab_exp_rep:
        st.markdown("### 📄 Formal Quality Audit Report Generator")
        st.caption("Generate reports documenting data provenance, configured checks, findings, and heuristic scores. These are not standards certifications.")

        rep_ind_name = st.selectbox("Select Indicator for Formal Audit", options=list(catalog_by_name.keys()), index=0, key="rep_ind_select")
        rep_ind = catalog_by_name[rep_ind_name]

        rep_runs = list_runs(db_url, limit=5, series_id=rep_ind.series_id)
        if rep_runs:
            latest_r = rep_runs[0]
            rep_details = get_run_details(db_url, latest_r["id"])
            if rep_details:
                known_gaps = getattr(rep_ind, "known_missing_periods", {})
                scorecard = calculate_quality_scorecard(rep_details["observations"], rep_details["findings"], rep_ind.start_year, known_missing_periods=known_gaps)
                audit_md = generate_markdown_audit_report(latest_r, rep_details["findings"], scorecard, rep_ind.name, indicator=rep_ind)

                st.download_button(
                    f"📥 Download Official Audit Report ({rep_ind.indicator_id}.md)",
                    data=audit_md,
                    file_name=f"audit_report_{rep_ind.indicator_id}_run_{latest_r['id']}.md",
                    mime="text/markdown",
                    type="primary",
                    use_container_width=True,
                )

                with st.expander("👁️ View Rendered Report Preview", expanded=True):
                    st.markdown(audit_md)
        else:
            st.info("No recorded audit runs for this indicator yet. Click 'Sync All Indicators' to generate audit logs.")

    with tab_exp_diff:
        st.markdown("### 🔄 Historical Revision Detection between Runs")
        st.caption("Compare consecutive historical pipeline runs to audit retrospective revisions published by national authorities (ELSTAT) and Eurostat.")

        diff_ind_name = st.selectbox("Select Series to Audit Revisions", options=list(catalog_by_name.keys()), index=0, key="diff_ind_select")
        diff_ind = catalog_by_name[diff_ind_name]

        diff_runs = list_runs(db_url, limit=10, series_id=diff_ind.series_id)
        if len(diff_runs) >= 2:
            col_r1, col_r2 = st.columns(2)
            run_opts = {f"Run #{r['id']} ({r['checked_at'][:19].replace('T', ' ')} UTC, {r['status']})": r["id"] for r in diff_runs}
            with col_r1:
                run_a_label = st.selectbox("Baseline Run (Earlier)", options=list(run_opts.keys()), index=1)
            with col_r2:
                run_b_label = st.selectbox("Comparison Run (Later)", options=list(run_opts.keys()), index=0)

            run_a_id = run_opts[run_a_label]
            run_b_id = run_opts[run_b_label]

            details_a = get_run_details(db_url, run_a_id)
            details_b = get_run_details(db_url, run_b_id)

            if details_a and details_b:
                diff_outcome = compare_run_snapshots(details_a["observations"], details_b["observations"])
                if diff_outcome["has_changes"]:
                    st.warning(f"Detected {diff_outcome['revised_count']} revised value(s) between Run #{run_a_id} and Run #{run_b_id}!")
                    df_diff_table = pd.DataFrame(diff_outcome["diffs"])
                    st.dataframe(df_diff_table, use_container_width=True)
                else:
                    st.success(f"✅ Zero historical revisions detected between Run #{run_a_id} and Run #{run_b_id}. All observations remained strictly identical.")
        else:
            st.info("At least two ingestion runs are required to perform historical revision audits. Sync indicators again to record a second run.")

    with tab_exp_api:
        st.markdown("### 🔗 Developer & Researcher Wire API Reference")
        st.caption("Direct, unauthenticated public API wire endpoints for reproducible academic and econometric research.")

        api_ind_name = st.selectbox("Select Indicator for API Wire Details", options=list(catalog_by_name.keys()), index=0, key="api_ind_select")
        api_ind = catalog_by_name[api_ind_name]

        st.markdown(
            f"""
            - **Indicator:** `{api_ind.name}`
            - **Eurostat Dataset Code:** `{api_ind.dataset_code}`
            - **SDMX 2.1 Filter Key:** `{api_ind.series_key}`
            - **Direct Dissemination URL:** [{api_ind.api_url}]({api_ind.api_url})
            - **Reuse Terms:** European Commission Open Data Policy (free reuse with attribution).
            """
        )

        st.markdown("#### Reproducible Python Snippet")
        st.code(
            f"""import requests
import pandas as pd

url = "{api_ind.api_url}"
response = requests.get(url, timeout=30)
response.raise_for_status()

# Eurostat SDMX TSV structure
lines = response.text.strip().split('\\n')
header = [h.strip() for h in lines[0].split('\\t')]
print("Header columns:", header)
""",
            language="python",
        )


# ==============================================================================
# PAGE 8: 📈 GREECE: PROGRESS & CHALLENGES
# ==============================================================================
elif page == "📈 Greece: Progress & Challenges":
    title = "📈 Η πορεία της Ελλάδας: πρόοδος και προκλήσεις" if greek_language else "📈 Greece: Progress & Challenges"
    subtitle = (
        "Ισορροπημένη εικόνα για τους τομείς όπου η Ελλάδα βελτιώνεται, όπου υπάρχουν πιέσεις και όπου χρειάζεται προσεκτική ερμηνεία."
        if greek_language
        else "A balanced snapshot of where Greece is improving, where pressures remain, and which signals need context."
    )
    st.markdown(f'<div class="brand-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="brand-subtitle">{subtitle}</div>', unsafe_allow_html=True)

    indicator_names_el = {
        "gdp_nominal": "Ακαθάριστο Εγχώριο Προϊόν (ονομαστικό)",
        "gdp_real": "Ακαθάριστο Εγχώριο Προϊόν (πραγματικό)",
        "inflation_rate": "Πληθωρισμός (ΕνΔΤΚ)",
        "unemployment_rate": "Ποσοστό ανεργίας",
        "public_debt_pct": "Δημόσιο χρέος (% ΑΕΠ)",
        "trade_exports": "Εξαγωγές αγαθών και υπηρεσιών",
        "trade_imports": "Εισαγωγές αγαθών και υπηρεσιών",
        "population": "Πληθυσμός",
        "life_expectancy": "Προσδόκιμο ζωής κατά τη γέννηση",
        "poverty_rate": "Κίνδυνος φτώχειας",
        "immigration_flow": "Ετήσια εισερχόμενη μετανάστευση",
        "emigration_flow": "Ετήσια εξερχόμενη μετανάστευση",
        "renewable_energy_share": "Μερίδιο ανανεώσιμης ενέργειας",
        "ghg_emissions": "Εκπομπές αερίων του θερμοκηπίου",
        "energy_consumption": "Τελική κατανάλωση ενέργειας",
        "tourist_arrivals": "Τουριστικές αφίξεις",
        "tourist_nights": "Διανυκτερεύσεις τουριστών",
        "house_price_index": "Δείκτης τιμών κατοικιών",
        "bond_yield_10y": "Απόδοση 10ετούς κρατικού ομολόγου",
    }
    interpretation_el = {
        "gdp_nominal": "Το ονομαστικό ΑΕΠ περιλαμβάνει τις αυξήσεις τιμών. Για την πραγματική αύξηση της παραγωγής εξετάστε και το πραγματικό ΑΕΠ.",
        "gdp_real": "Η παραγωγή αυξήθηκε μετά την προσαρμογή για τις μεταβολές τιμών· αυτό δεν δείχνει πώς κατανέμεται η ανάπτυξη.",
        "inflation_rate": "Χαμηλότερος πληθωρισμός σημαίνει βραδύτερη αύξηση τιμών, όχι απαραίτητα πτώση του γενικού επιπέδου τιμών.",
        "unemployment_rate": "Η μείωση της ανεργίας είναι συνήθως θετική, αλλά ο δείκτης δεν περιγράφει μισθούς ή ποιότητα εργασίας.",
        "public_debt_pct": "Ο λόγος χρέους προς ΑΕΠ μπορεί να μειωθεί ακόμη κι αν αυξάνεται το συνολικό δημόσιο χρέος.",
        "trade_exports": "Οι εξαγωγές μετρώνται σε τρέχουσες τιμές, οπότε επηρεάζονται και από τις τιμές και από τις ποσότητες.",
        "trade_imports": "Οι εισαγωγές στηρίζουν κατανάλωση και παραγωγή· η αύξηση ή μείωσή τους από μόνη της δεν δείχνει οικονομική υγεία.",
        "population": "Η πληθυσμιακή μεταβολή επηρεάζεται από γεννήσεις, θανάτους και μετανάστευση· η κατεύθυνσή της δεν είναι από μόνη της θετική ή αρνητική.",
        "life_expectancy": "Η αύξηση είναι θετική ένδειξη για την υγεία του πληθυσμού, αλλά δεν αποτυπώνει τις ανισότητες στην υγεία.",
        "poverty_rate": "Η μείωση του σχετικού κινδύνου φτώχειας είναι θετική, αλλά δεν καλύπτει κάθε μορφή οικονομικής δυσκολίας.",
        "immigration_flow": "Εξετάστε τον δείκτη μαζί με την εξερχόμενη μετανάστευση· είναι εισροή και όχι καθαρή μετανάστευση.",
        "emigration_flow": "Εξετάστε τον δείκτη μαζί με την εισερχόμενη μετανάστευση· είναι εκροή και όχι καθαρή μετανάστευση.",
        "renewable_energy_share": "Η αύξηση δείχνει ότι οι ανανεώσιμες πηγές καλύπτουν μεγαλύτερο μερίδιο της τελικής ενεργειακής κατανάλωσης.",
        "ghg_emissions": "Οι χαμηλότερες εκπομπές είναι θετική ένδειξη για την κλιματική πρόοδο· ελέγξτε την κάλυψη και τις αναθεωρήσεις.",
        "energy_consumption": "Η μεταβολή μπορεί να οφείλεται σε αποδοτικότητα, καιρό ή οικονομική δραστηριότητα· καμία κατεύθυνση δεν είναι πάντα καλύτερη.",
        "tourist_arrivals": "Οι περισσότερες αφίξεις μπορούν να ενισχύσουν τον τουρισμό, αλλά και να πιέσουν κατοικίες, υποδομές και υπηρεσίες.",
        "tourist_nights": "Οι περισσότερες διανυκτερεύσεις στηρίζουν την τουριστική δραστηριότητα· έχει σημασία και η εποχικότητα και η τοπική χωρητικότητα.",
        "house_price_index": "Η άνοδος των ονομαστικών τιμών μπορεί να δυσκολεύει την προσιτή στέγαση· και η πτώση χρειάζεται πλαίσιο εισοδημάτων και προσφοράς.",
        "bond_yield_10y": "Η χαμηλότερη απόδοση μπορεί να μειώσει το κόστος νέου δανεισμού· δεν αλλάζει τους τόκους όλου του υφιστάμενου χρέους.",
    }

    histories = {
        ind.indicator_id: get_latest_observations(db_url, ind.series_id)
        for ind in INDICATOR_CATALOG
    }
    year_options = sorted(
        {
            observation.period
            for observations in histories.values()
            for observation in observations
            if observation.value is not None and isfinite(observation.value)
        }
    )
    if len(year_options) < 2:
        st.warning(
            "Χρειάζονται τουλάχιστον δύο έτη αποθηκευμένων στοιχείων. Κάντε συγχρονισμό των δεικτών και δοκιμάστε ξανά."
            if greek_language
            else "At least two years of stored observations are needed for a comparison. Sync the indicators, then try again."
        )
        st.stop()

    date_cols = st.columns(2)
    with date_cols[0]:
        year_from = st.selectbox(
            "Έτος έναρξης" if greek_language else "Start year",
            options=year_options,
            index=max(0, len(year_options) - 2),
            key="assessment_start_year",
        )
    with date_cols[1]:
        year_to = st.selectbox(
            "Έτος λήξης" if greek_language else "End year",
            options=year_options,
            index=len(year_options) - 1,
            key="assessment_end_year",
        )

    if year_to <= year_from:
        st.warning(
            "Το έτος λήξης πρέπει να είναι μετά το έτος έναρξης."
            if greek_language
            else "End year must be later than start year."
        )
        st.stop()

    st.caption(
        "Τα στοιχεία είναι ετήσια· επιλέξτε έτος έναρξης και έτος λήξης για τη σύγκριση."
        if greek_language
        else "The data is annual. Choose a start year and end year for the comparison."
    )
    st.caption(
        (
            f"Σύγκριση {year_from} με {year_to}. Τα διαθέσιμα έτη διαφέρουν ανά δείκτη και δεν υπάρχουν στοιχεία για κάθε έτος σε όλες τις σειρές. "
            "Οι μεταβολές δείχνουν τάσεις, όχι ότι ένα συγκεκριμένο γεγονός ή μέτρο προκάλεσε την αλλαγή."
            if greek_language
            else f"Comparing {year_from} with {year_to}. The publication years can differ by indicator, and not every series has data in every year. "
            "These are signs of progress or pressure, not proof that a particular event or policy caused the change."
        )
    )

    catalog_by_id = {ind.indicator_id: ind for ind in INDICATOR_CATALOG}

    # For these indicators, a particular direction is usually a favorable signal.
    favorable_direction = {
        "gdp_real": "up",
        "unemployment_rate": "down",
        "inflation_rate": "down",
        "public_debt_pct": "down",
        "life_expectancy": "up",
        "poverty_rate": "down",
        "renewable_energy_share": "up",
        "ghg_emissions": "down",
        "bond_yield_10y": "down",
    }
    # A rise in house prices can increase affordability pressure. A fall is
    # ambiguous without information about incomes, rents, supply, and housing investment.
    pressure_direction = {"house_price_index": "up"}
    interpretation = {
        "gdp_nominal": "Nominal GDP includes price increases. Check real GDP before treating a rise as more output.",
        "gdp_real": "Inflation-adjusted output rose; this is a broad growth signal, not a measure of how growth is shared.",
        "inflation_rate": "A lower rate means prices are rising more slowly; it does not mean the overall price level fell.",
        "unemployment_rate": "A lower rate is usually positive for work opportunities, though it does not describe wages or job quality.",
        "public_debt_pct": "The debt ratio compares debt with GDP. It can fall even if the total debt stock grows.",
        "trade_exports": "Export values are in current euros, so prices as well as quantities can move them.",
        "trade_imports": "Imports support consumption and production; a rise or fall alone is not a verdict on economic health.",
        "population": "Population change reflects births, deaths, and migration; the direction alone is not inherently good or bad.",
        "life_expectancy": "A rise is a positive population health signal, but it does not describe health inequalities.",
        "poverty_rate": "A lower relative-poverty rate is positive, but it does not capture every form of hardship.",
        "immigration_flow": "Interpret alongside emigration and population data; this is an inflow count, not net migration.",
        "emigration_flow": "Interpret alongside immigration and population data; this is an outflow count, not net migration.",
        "renewable_energy_share": "A rising share indicates renewables account for more gross final energy use.",
        "ghg_emissions": "Lower emissions are positive for climate progress; check coverage and revisions when comparing years.",
        "energy_consumption": "Changes can reflect efficiency, weather, or economic activity, so neither direction is automatically better.",
        "tourist_arrivals": "More arrivals can support tourism activity but can also add pressure to housing, infrastructure, and local services.",
        "tourist_nights": "More overnight stays can support tourism activity; consider seasonal concentration and local capacity too.",
        "house_price_index": "Rising nominal prices can make housing less affordable; falling prices also need context on incomes and supply.",
        "bond_yield_10y": "A lower benchmark yield can ease the cost of new borrowing; it does not reset interest on all existing debt.",
    }

    grouped = {"Improving": [], "Needs attention": [], "Mixed or unclear": []}

    def readable_value(ind: IndicatorDefinition, value: float | None) -> str:
        if value is None:
            return "—"
        if greek_language:
            if ind.indicator_id in {"gdp_nominal", "gdp_real", "trade_exports", "trade_imports"}:
                number = f"{value / 1_000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return f"{number} δισ. €"
            if ind.indicator_id in {"population", "immigration_flow", "emigration_flow"}:
                number = f"{value:,.0f}".replace(",", ".")
                return f"{number} άτομα"
            if ind.indicator_id == "life_expectancy":
                return f"{value:.1f}".replace(".", ",") + " έτη"
            if ind.indicator_id in {"tourist_arrivals", "tourist_nights"}:
                number = f"{value:,.0f}".replace(",", ".")
                unit = "αφίξεις" if ind.indicator_id == "tourist_arrivals" else "διανυκτερεύσεις"
                return f"{number} {unit}"
            if ind.indicator_id == "ghg_emissions":
                number = f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return f"{number} χιλ. τόνοι CO₂e"
            if ind.indicator_id == "energy_consumption":
                return f"{value:.2f}".replace(".", ",") + " Mtoe"
            if ind.indicator_id == "house_price_index":
                return f"{value:.2f}".replace(".", ",")
            return f"{value:.2f}".replace(".", ",") + "%"
        if ind.indicator_id in {"gdp_nominal", "gdp_real"}:
            return f"€{value / 1_000:,.1f}B"
        return format_indicator_value(value, ind.unit, ind.unit_short)

    for indicator_id, observations in histories.items():
        ind = catalog_by_id[indicator_id]
        by_period = {
            observation.period: observation.value
            for observation in observations
            if observation.value is not None and isfinite(observation.value)
        }
        start_value = by_period.get(year_from)
        end_value = by_period.get(year_to)
        has_comparison = start_value is not None and end_value is not None
        delta = None
        change_display = "Change unavailable"
        if has_comparison and ind.change_metric != "disabled":
            difference = end_value - start_value
            if ind.change_metric == "percentage_points":
                delta = difference
                change_display = (
                    f"{difference:+.2f} π.μ.".replace(".", ",")
                    if greek_language
                    else f"{difference:+.2f} pp"
                )
            elif abs(start_value) >= 1e-6:
                delta = difference / abs(start_value) * 100
                change_display = (
                    f"{delta:+.2f}%".replace(".", ",")
                    if greek_language
                    else f"{delta:+.2f}%"
                )

        direction = "up" if has_comparison and end_value > start_value else "down"
        is_stable = (
            has_comparison
            and delta is not None
            and abs(delta) < (0.01 if ind.change_metric == "percentage_points" else 0.1)
        )
        if not has_comparison or delta is None:
            category = "Mixed or unclear"
            trend = (
                "Δεν υπάρχουν στοιχεία για τα επιλεγμένα έτη" if greek_language and not has_comparison
                else "Η μεταβολή δεν υπολογίζεται" if greek_language
                else "Missing data for selected years" if not has_comparison
                else "Change unavailable"
            )
        elif is_stable:
            category = "Mixed or unclear"
            trend = f"Σχεδόν αμετάβλητο ({change_display})" if greek_language else f"Broadly stable ({change_display})"
        elif ind.indicator_id in favorable_direction:
            expected = favorable_direction[ind.indicator_id]
            category = "Improving" if direction == expected else "Needs attention"
            trend = f"{'↑' if direction == 'up' else '↓'} {change_display}"
        elif ind.indicator_id in pressure_direction:
            expected = pressure_direction[ind.indicator_id]
            category = "Needs attention" if direction == expected else "Mixed or unclear"
            trend = f"{'↑' if direction == 'up' else '↓'} {change_display}"
        else:
            category = "Mixed or unclear"
            trend = f"{'↑' if direction == 'up' else '↓'} {change_display}"

        grouped[category].append(
            {
                "indicator": ind,
                "start_value": start_value,
                "end_value": end_value,
                "year_from": year_from,
                "year_to": year_to,
                "trend": trend,
                "explanation": interpretation_el.get(ind.indicator_id, ind.description) if greek_language else interpretation.get(ind.indicator_id, ind.description),
            }
        )

    summary_cols = st.columns(3)
    summary_cols[0].metric("Θετικές εξελίξεις" if greek_language else "Improving signals", len(grouped["Improving"]))
    summary_cols[1].metric("Υπό πίεση" if greek_language else "Needs attention", len(grouped["Needs attention"]))
    summary_cols[2].metric("Μικτή εικόνα / λίγα στοιχεία" if greek_language else "Mixed / limited evidence", len(grouped["Mixed or unclear"]))

    st.markdown("### 🟢 Τομείς με θετική πορεία" if greek_language else "### 🟢 Areas moving in a positive direction")
    st.caption("Οι δείκτες αυτοί κινήθηκαν προς κατεύθυνση που θεωρείται γενικά θετική για το συγκεκριμένο μέγεθος." if greek_language else "These indicators moved in a direction that is generally favorable for the measure shown.")

    def render_assessment(items: list[dict[str, Any]], empty_message: str) -> None:
        if not items:
            st.caption(empty_message)
            return
        for entry in items:
            ind = entry["indicator"]
            start_text = readable_value(ind, entry["start_value"])
            end_text = readable_value(ind, entry["end_value"])
            cols = st.columns([2.1, 1, 1, 3])
            indicator_name = indicator_names_el.get(ind.indicator_id, ind.name) if greek_language else ind.name
            cols[0].markdown(f"**{ind.topic_icon} {indicator_name}**  \n{entry['trend']}")
            cols[1].caption(f"Αρχή · {entry['year_from']}" if greek_language else f"Start · {entry['year_from']}")
            cols[1].write(start_text)
            cols[2].caption(f"Τέλος · {entry['year_to']}" if greek_language else f"End · {entry['year_to']}")
            cols[2].write(end_text)
            cols[3].write(entry["explanation"])

    render_assessment(grouped["Improving"], "Δεν υπάρχουν ακόμη σαφείς θετικές μεταβολές για την επιλεγμένη περίοδο." if greek_language else "No clearly positive movements are available for the selected period.")
    st.markdown("### 🟠 Τομείς υπό πίεση" if greek_language else "### 🟠 Areas under pressure")
    st.caption("Οι δείκτες αυτοί κινήθηκαν προς κατεύθυνση που μπορεί να σημαίνει επιδείνωση." if greek_language else "These indicators moved in a direction that can signal a worsening outcome for the measure shown.")
    render_assessment(grouped["Needs attention"], "Δεν υπάρχουν σαφείς αρνητικές μεταβολές στα αποθηκευμένα στοιχεία της περιόδου." if greek_language else "No clear worsening movements are available in the stored data for this period.")
    st.markdown("### ⚖️ Μικτά μηνύματα ή περιορισμένα στοιχεία" if greek_language else "### ⚖️ Mixed signals or limited evidence")
    st.caption("Αυτοί οι δείκτες χρειάζονται πρόσθετο πλαίσιο, έμειναν σχεδόν σταθεροί ή δεν έχουν στοιχεία και για τα δύο έτη." if greek_language else "These indicators need extra context, were broadly stable, or do not have data for both years.")
    render_assessment(grouped["Mixed or unclear"], "Δεν υπάρχουν δείκτες σε αυτή την κατηγορία." if greek_language else "No indicators in this group.")

    st.info(
        "Η σελίδα δείχνει τάσεις, όχι συνολική βαθμολογία ή αιτίες. Η βελτίωση σε έναν δείκτη δεν αναιρεί τις πιέσεις σε άλλον. Δείτε τις **Πηγές και Μεθοδολογία** για ορισμούς και περιορισμούς."
        if greek_language
        else "This is a directional snapshot, not an overall grade for Greece. It does not identify causes, "
        "and a favorable movement in one measure does not cancel out pressure in another. Open "
        "**Sources & Methodology** to review definitions, sources, and limitations."
    )


# ==============================================================================
# PAGE 9: ℹ️ SOURCES & METHODOLOGY
# ==============================================================================
elif page == "ℹ️ Sources & Methodology":
    st.markdown('<div class="brand-title">ℹ️ Sources, Methodology & Data Architecture</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Complete transparency regarding official data sources, API endpoints, classification standards, '
        'known limitations, and the pipeline architecture. Zero invented or placeholder observations.</div>',
        unsafe_allow_html=True,
    )

    # Searchable Central Indicator Catalog Directory
    st.markdown("### 📚 Official Indicator Catalog Directory")
    cat_search = st.text_input("Filter Catalog Table", placeholder="Search by name, topic, dataset code...").strip().lower()

    cat_rows = []
    for ind in INDICATOR_CATALOG:
        if cat_search and cat_search not in f"{ind.name} {ind.topic} {ind.dataset_code} {ind.unit}".lower():
            continue
        cat_rows.append({
            "Topic": f"{ind.topic_icon} {ind.topic}",
            "Indicator": ind.name,
            "Dataset Code": ind.dataset_code,
            "SDMX Series Key": ind.series_key,
            "Unit": ind.unit_short,
            "Frequency": ind.frequency,
            "Official Source": ind.source_name,
            "Direct Portal URL": ind.source_url,
        })

    st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, height=320)

    st.markdown("---")

    # Indicator Deep Dive
    st.markdown("### 🔬 Indicator Methodology Deep Dive")
    ind_names_map = {f"{ind.topic_icon} {ind.name}": ind for ind in INDICATOR_CATALOG}
    sel_ind_deep = st.selectbox("Select Indicator for Detailed Methodology & Dimensions", options=list(ind_names_map.keys()), index=0)
    ind_obj = ind_names_map[sel_ind_deep]

    meta_cols = st.columns(2)
    with meta_cols[0]:
        st.markdown(f"**Indicator Name:** {ind_obj.name}")
        st.markdown(f"**Topic:** {ind_obj.topic_icon} {ind_obj.topic}")
        st.markdown(f"**Measurement Unit:** {ind_obj.unit}")
        st.markdown(f"**Dataset Code:** `{ind_obj.dataset_code}`")
        st.markdown(f"**SDMX Filter Key:** `{ind_obj.series_key}`")
        st.markdown(f"**Source Authority:** [{ind_obj.source_name}]({ind_obj.source_url})")
    with meta_cols[1]:
        st.markdown(f"**Description:** {ind_obj.description}")
        st.markdown(f"**Methodology Standard:** {ind_obj.methodology}")
        st.markdown(f"**Known Limitations & Breaks:** {ind_obj.limitations}")
        st.markdown(f"**Coverage Start Year:** {ind_obj.start_year}")
        st.markdown(f"**Direct API Endpoint:** [Eurostat SDMX TSV URL]({ind_obj.api_url})")

    st.markdown("---")

    # Documented Limitations & Excluded Topics
    st.markdown("### ⚠️ Documented Scope Limitations & Excluded Topics")
    st.markdown(
        "In strict adherence to our **zero-placeholder, zero-synthetic-data policy**, we do not invent or hardcode observations "
        "when an indicator lacks an open, unauthenticated public REST API. The limitations below are documented transparently:"
    )

    for key, doc in TOPIC_LIMITATIONS_DOCUMENTATION.items():
        st.markdown(
            f"""
            <div class="callout-box">
                <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.25rem;">
                    {doc['topic']}: {doc['indicator_label']}
                </div>
                <div style="color:#94a3b8; font-size:0.85rem; margin-bottom:0.4rem;">
                    <strong>Authority:</strong> {doc['official_authority']} |
                    <strong>Access Method:</strong> {doc['access_method']} |
                    <a href="{doc['direct_link']}" target="_blank" style="color:#38bdf8;">Official Portal</a>
                </div>
                <div style="font-size:0.9rem; line-height:1.4;">
                    {doc['why_not_direct_api']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Data Pipeline Architecture
    st.markdown("### 🏗️ Data Architecture & Pipeline Resilience")
    st.markdown(
        """
        - **Central Indicator Catalog:** Single source of truth in `src/greek_data_monitor/catalog.py` governing all dimensions, units, sources, and thresholds.
        - **Independent Failure Isolation:** Each source and indicator ingests independently. An upstream failure or network timeout on one dataset never hides other monitored data.
        - **Snapshot Persistence & Revision Tracking:** SQLite tables (`quality_runs`, `observations`, `country_benchmarks`) preserve historical snapshots rather than overwriting past runs, enabling retrospective revision audits.
        - **No Secret Leaks:** Ingestion utilizes unauthenticated public dissemination APIs (Eurostat SDMX 2.1, ECB Data Portal); no API tokens or credentials are stored or exposed.
        """
    )
