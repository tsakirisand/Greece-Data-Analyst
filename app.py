from __future__ import annotations

import io
from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from greek_data_monitor.config import DEFAULT_SERIES, Settings
from greek_data_monitor.dashboard_service import (
    compare_run_snapshots,
    filter_and_sort_observations,
    format_gdp_value,
    get_flag_descriptions,
    get_quality_rule_descriptions,
)
from greek_data_monitor.ingestion import IngestionError, fetch_eurostat_series
from greek_data_monitor.quality import inspect
from greek_data_monitor.store import (
    get_latest_observations,
    get_run_details,
    list_runs,
    save_run,
)

st.set_page_config(
    page_title="Greek Public Data Quality Monitor",
    page_icon="🇬🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Accessible CSS styling
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
        color: #475569;
        font-size: 0.98rem;
        margin-bottom: 1.2rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1;
        letter-spacing: 0.02em;
    }
    .badge-pass { background-color: #dcfce7; color: #14532d; border: 1px solid #86efac; }
    .badge-warn { background-color: #fef3c7; color: #78350f; border: 1px solid #fde68a; }
    .badge-error { background-color: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; }
    .badge-info { background-color: #e0f2fe; color: #0c4a6e; border: 1px solid #7dd3fc; }
    .card-kpi {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 1rem 1.15rem;
    }
    .card-kpi-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .card-kpi-val {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 0.25rem;
    }
    .card-kpi-sub {
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 0.2rem;
    }
    .callout-box {
        background: #f1f5f9;
        border-left: 4px solid #0284c7;
        padding: 0.85rem 1.1rem;
        border-radius: 0 0.5rem 0.5rem 0;
        margin-bottom: 1.2rem;
        font-size: 0.92rem;
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
st.sidebar.caption("Official Statistics Surveillance for Greece")

# Page Navigation
page = st.sidebar.radio(
    "Navigation",
    options=[
        "📌 Overview",
        "🔍 Data Explorer",
        "🛡️ Quality Checks",
        "📜 Run History",
        "ℹ️ Source & Methodology",
    ],
    index=0,
)

st.sidebar.markdown("---")

# Settings & Thresholds
with st.sidebar.expander("⚙️ Monitor Settings", expanded=False):
    db_url = st.text_input("Database URL", value=settings.database_url)
    yoy_threshold = st.slider(
        "YoY Review Threshold (%)",
        min_value=5.0,
        max_value=60.0,
        value=settings.max_abs_yoy_change_pct,
        step=1.0,
        help="Annual percentage swings exceeding this threshold trigger a review warning (WARN).",
    )
    min_year = st.number_input(
        "Series Start Year",
        min_value=1950,
        max_value=2030,
        value=settings.min_year if settings.min_year else 1995,
        help="Eurostat ESA 2010 GDP coverage for Greece begins in 1995. Missing values prior to this year are treated as informational pre-coverage.",
    )

# Manual On-Demand Ingestion Trigger
st.sidebar.markdown("### Data Refresh")
if st.sidebar.button("🚀 Fetch & Run Quality Check", type="primary", use_container_width=True):
    with st.spinner("Connecting to Eurostat API, evaluating quality rules, and persisting snapshot..."):
        try:
            previous_obs = get_latest_observations(db_url, DEFAULT_SERIES.series_id)
            fetched_obs = fetch_eurostat_series(DEFAULT_SERIES, timeout=settings.request_timeout_seconds)
            findings = inspect(
                fetched_obs,
                threshold_pct=yoy_threshold,
                previous_observations=previous_obs,
                min_year=int(min_year),
            )
            new_run_id = save_run(
                database_url=db_url,
                observations=fetched_obs,
                findings=findings,
                series_id=DEFAULT_SERIES.series_id,
            )
            st.sidebar.success(f"Run #{new_run_id} successfully executed and saved!")
            st.rerun()
        except IngestionError as exc:
            st.sidebar.error(f"Ingestion failed: {exc}")
        except Exception as exc:
            st.sidebar.error(f"Unexpected error: {exc}")

# Load Run History from Database
runs = list_runs(db_url, limit=30)

if not runs:
    st.markdown('<div class="brand-title">🇬🇷 Greek Public Data Quality Monitor</div>', unsafe_allow_html=True)
    st.warning("No quality runs found in database. Click **'Fetch & Run Quality Check'** in the sidebar to perform your first live monitoring run.")
    st.stop()

# Snapshot Selector for Inspection
st.sidebar.markdown("---")
st.sidebar.markdown("### Snapshot Selector")
run_map = {
    f"Run #{r['id']} — {r['checked_at'][:19]} ({r['status']})": r["id"]
    for r in runs
}
selected_run_label = st.sidebar.selectbox("Inspect Monitoring Run", options=list(run_map.keys()), index=0)
selected_run_id = run_map[selected_run_label]

# Load current run details
current_run_data = get_run_details(db_url, selected_run_id)
if not current_run_data:
    st.error(f"Could not load data for Run #{selected_run_id}")
    st.stop()

current_run = current_run_data["run"]
observations = current_run_data["observations"]
findings = current_run_data["findings"]

# Identify previous run if exists
previous_run_id: int | None = None
for r in runs:
    if r["id"] < selected_run_id:
        previous_run_id = r["id"]
        break

previous_run_data = get_run_details(db_url, previous_run_id) if previous_run_id else None

# Prepare numerical observations for analytics
df_obs = pd.DataFrame(observations)
if not df_obs.empty and "value" in df_obs.columns:
    df_obs["period"] = pd.to_numeric(df_obs["period"])
    df_obs["value"] = pd.to_numeric(df_obs["value"])
    df_numeric = df_obs.dropna(subset=["value"]).sort_values("period").reset_index(drop=True)
    df_numeric["yoy_change_pct"] = df_numeric["value"].pct_change() * 100.0
else:
    df_numeric = pd.DataFrame()


def render_status_badge(status: str) -> str:
    """Accessible badge with distinct icons, color contrast, and text."""
    if status == "PASS":
        return '<span class="badge badge-pass">✅ PASS</span>'
    elif status == "WARN" or status == "WARNING":
        return '<span class="badge badge-warn">⚠️ WARN</span>'
    elif status == "ERROR" or status == "FAIL":
        return '<span class="badge badge-error">❌ FAIL / ERROR</span>'
    return '<span class="badge badge-info">ℹ️ INFO</span>'


# =========================================================
# PAGE 1: OVERVIEW
# =========================================================
if page == "📌 Overview":
    st.markdown('<div class="brand-title">🇬🇷 Greek Public Data Quality Monitor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Real-time surveillance, historical revision auditing, and statistical integrity checks for Greece\'s annual GDP.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="callout-box">
            <b>Series Being Monitored:</b> Greece Annual Gross Domestic Product (GDP at market prices) • 
            <b>Eurostat Code:</b> <code>nama_10_gdp</code> • <b>Geography:</b> Greece (<code>EL</code>) • 
            <b>Unit:</b> Current prices, million euro (<code>CP_MEUR</code>) • <b>Frequency:</b> Annual (<code>A</code>)
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top KPI summary cards
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="card-kpi">
                <div class="card-kpi-title">Audit Status (Run #{current_run['id']})</div>
                <div class="card-kpi-val">{render_status_badge(current_run['status'])}</div>
                <div class="card-kpi-sub">Errors: {current_run['error_count']} • Warnings: {current_run['warning_count']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        if not df_numeric.empty:
            latest_row = df_numeric.iloc[-1]
            latest_val = latest_row["value"]
            latest_yr = int(latest_row["period"])
            flag = latest_row.get("source_status")
            flag_note = f" (Flag: <code>{flag}</code> provisional)" if flag == "p" else (f" (Flag: <code>{flag}</code>)" if flag else " (Finalized)")
            st.markdown(
                f"""
                <div class="card-kpi">
                    <div class="card-kpi-title">Latest GDP ({latest_yr})</div>
                    <div class="card-kpi-val">€{latest_val:,.1f} M</div>
                    <div class="card-kpi-sub">{flag_note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="card-kpi">
                    <div class="card-kpi-title">Latest GDP</div>
                    <div class="card-kpi-val">N/A</div>
                    <div class="card-kpi-sub">No numeric values</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with k3:
        if not df_numeric.empty and len(df_numeric) > 1:
            latest_yoy = df_numeric.iloc[-1]["yoy_change_pct"]
            prev_yr = int(df_numeric.iloc[-2]["period"])
            cur_yr = int(df_numeric.iloc[-1]["period"])
            trend_icon = "📈" if latest_yoy >= 0 else "📉"
            st.markdown(
                f"""
                <div class="card-kpi">
                    <div class="card-kpi-title">Latest YoY Growth</div>
                    <div class="card-kpi-val">{trend_icon} {latest_yoy:+.2f}%</div>
                    <div class="card-kpi-sub">{prev_yr} to {cur_yr} change</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="card-kpi">
                    <div class="card-kpi-title">Latest YoY Growth</div>
                    <div class="card-kpi-val">N/A</div>
                    <div class="card-kpi-sub">Insufficient history</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with k4:
        checked_time = current_run["checked_at"][:19].replace("T", " ")
        st.markdown(
            f"""
            <div class="card-kpi">
                <div class="card-kpi-title">Observations & Retrieval</div>
                <div class="card-kpi-val">{len(observations)} periods</div>
                <div class="card-kpi-sub">Retrieved: {checked_time} UTC</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Time-Series Chart
    st.subheader("📈 Greek Annual GDP Time Series (Eurostat nama_10_gdp)")
    if not df_numeric.empty:
        fig_ts = go.Figure()

        # Add line trace
        fig_ts.add_trace(
            go.Scatter(
                x=df_numeric["period"],
                y=df_numeric["value"],
                mode="lines+markers",
                name="Annual GDP",
                line=dict(color="#0284c7", width=2.5),
                marker=dict(size=7, color="#0369a1"),
                hovertemplate="<b>Year %{x}</b><br>GDP: €%{y:,.1f} M<extra></extra>",
            )
        )

        # Highlight provisional observations
        df_prov = df_numeric[df_numeric["source_status"] == "p"]
        if not df_prov.empty:
            fig_ts.add_trace(
                go.Scatter(
                    x=df_prov["period"],
                    y=df_prov["value"],
                    mode="markers",
                    name="Provisional (Flag 'p')",
                    marker=dict(size=11, color="#f59e0b", symbol="diamond"),
                    hovertemplate="<b>Year %{x} (Provisional)</b><br>GDP: €%{y:,.1f} M<extra></extra>",
                )
            )

        fig_ts.update_layout(
            template="plotly_white",
            hovermode="x unified",
            xaxis=dict(title="Year", tickmode="linear", dtick=5, gridcolor="#f1f5f9"),
            yaxis=dict(title="Gross Domestic Product (Million EUR)", gridcolor="#f1f5f9"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=30, b=40),
            height=380,
        )
        st.plotly_chart(fig_ts, use_container_width=True)
    else:
        st.info("No numeric observations to display in chart.")

    # "What Changed?" Section
    st.markdown("---")
    st.subheader("🔍 What Changed Compared to the Previous Run?")
    if previous_run_data:
        comp = compare_run_snapshots(previous_run_data["observations"], observations)
        p_id = previous_run_data["run"]["id"]
        p_time = previous_run_data["run"]["checked_at"][:19].replace("T", " ")

        st.caption(f"Comparing Current Run #{selected_run_id} with Previous Run #{p_id} (recorded {p_time} UTC).")

        if not comp["has_changes"]:
            st.success(f"✅ **No changes detected:** All {comp['unchanged_count']} observations exactly match Run #{p_id}. No historical revisions or additions occurred.")
        else:
            st.warning(f"⚠️ **{comp['summary']}**")

            diff_df = pd.DataFrame(comp["diffs"])
            if not diff_df.empty:
                display_diff = diff_df.rename(
                    columns={
                        "period": "Year",
                        "change_type": "Change Type",
                        "old_value": f"Run #{p_id} Value",
                        "new_value": f"Run #{selected_run_id} Value",
                        "old_status": f"Run #{p_id} Flag",
                        "new_status": f"Run #{selected_run_id} Flag",
                        "value_diff": "Net Difference",
                    }
                )
                st.dataframe(display_diff, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ **First recorded run:** No previous historical snapshot exists in the database for comparison yet. Run another check to observe revisions over time.")


# =========================================================
# PAGE 2: DATA EXPLORER
# =========================================================
elif page == "🔍 Data Explorer":
    st.markdown('<div class="brand-title">🔍 Data Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Interactive table of observations with filtering, searching, revision labeling, and CSV data export.</div>',
        unsafe_allow_html=True,
    )

    if df_obs.empty:
        st.warning("No observations found in current run.")
        st.stop()

    all_years = sorted(df_obs["period"].astype(int).tolist())
    min_yr, max_yr = (min(all_years), max(all_years)) if all_years else (1975, 2025)

    # Filter controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 1.5])

    with f_col1:
        year_filter = st.slider("Filter Year Range", min_value=min_yr, max_value=max_yr, value=(min_yr, max_yr))

    with f_col2:
        status_filter = st.selectbox(
            "Filter Observation Type",
            options=["All", "Numeric only", "Missing values only", "Provisional only", "Flagged only"],
            index=0,
        )

    with f_col3:
        sort_choice = st.selectbox("Sort By", options=["Year (Period)", "Value"], index=0)
        sort_col = "period" if "Year" in sort_choice else "value"

    with f_col4:
        sort_order = st.radio("Order", options=["Ascending", "Descending"], index=0, horizontal=True)
        is_asc = sort_order == "Ascending"

    search_query = st.text_input("Search observations (e.g. '2024', 'p', ':')", value="")

    filtered_records = filter_and_sort_observations(
        observations=observations,
        year_range=year_filter,
        status_filter=status_filter,
        search_term=search_query,
        sort_by=sort_col,
        ascending=is_asc,
    )

    st.markdown(f"**Showing {len(filtered_records)} of {len(observations)} total observations:**")

    # Format table for display
    flag_defs = get_flag_descriptions()
    table_rows: list[dict[str, Any]] = []

    for item in filtered_records:
        val = item.get("value")
        status_flag = item.get("source_status")
        formatted_val = f"€{val:,.1f} M" if val is not None else "— (Missing)"
        flag_meaning = flag_defs.get(status_flag, "None / Finalized") if status_flag else "None / Finalized"

        # Label status visually
        if val is None:
            tag = "Missing (:)"
        elif status_flag == "p":
            tag = "Provisional (p)"
        elif status_flag == "b":
            tag = "Break in series (b)"
        else:
            tag = "Finalized numeric"

        table_rows.append(
            {
                "Year": int(item["period"]),
                "GDP (Million EUR)": formatted_val,
                "Numeric Value": val,
                "Data Status": tag,
                "Status Flag": status_flag or "—",
                "Flag Explanation": flag_meaning,
                "Unit": "CP_MEUR",
                "Retrieved At (UTC)": item.get("fetched_at", "")[:19].replace("T", " "),
            }
        )

    df_display = pd.DataFrame(table_rows)

    # Display interactive dataframe
    st.dataframe(
        df_display[["Year", "GDP (Million EUR)", "Data Status", "Status Flag", "Flag Explanation", "Unit", "Retrieved At (UTC)"]],
        use_container_width=True,
        hide_index=True,
    )

    # CSV Download Button
    csv_buffer = io.StringIO()
    df_display.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Export Filtered Data as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"greek_gdp_filtered_run_{selected_run_id}.csv",
        mime="text/csv",
        type="secondary",
    )


# =========================================================
# PAGE 3: QUALITY CHECKS
# =========================================================
elif page == "🛡️ Quality Checks":
    st.markdown('<div class="brand-title">🛡️ Quality Checks & Rule Findings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Structured evaluation of official statistics for missing values, duplicate periods, and historical revisions.</div>',
        unsafe_allow_html=True,
    )

    rule_defs = get_quality_rule_descriptions()

    # Rule glossary summary
    with st.expander("📖 Quality Rules Glossary & Plain-Language Explanations", expanded=False):
        st.markdown("Each observation undergoes verification against defined statistical quality rules:")
        for rule_key, info in rule_defs.items():
            st.markdown(f"**`{rule_key}` — {info['name']}** (Default: `{info['default_severity']}`)")
            st.markdown(f"- *What it checks:* {info['plain_explanation']}")
            st.markdown(f"- *Why it matters:* {info['why_it_matters']}")
            st.markdown(f"- *Guidance:* {info['review_guidance']}")
            st.markdown("---")

    st.subheader(f"Findings for Run #{selected_run_id}")
    st.caption(f"Evaluated on {current_run['checked_at'][:19].replace('T', ' ')} UTC • Total Observations: {current_run['observation_count']}")

    # Severity Filter
    f_sev = st.multiselect(
        "Filter Findings by Severity",
        options=["ERROR", "WARN", "INFO", "PASS"],
        default=["ERROR", "WARN", "INFO", "PASS"],
    )

    filtered_findings = [f for f in findings if f["severity"] in f_sev]

    if not filtered_findings:
        st.info("No findings match the selected severity filters.")
    else:
        for f in filtered_findings:
            sev = f["severity"]
            rule_key = f["rule"]
            msg = f["message"]
            period = f.get("period")
            period_badge = f" `Period {period}`" if period is not None else ""
            rule_info = rule_defs.get(rule_key, {})
            rule_title = rule_info.get("name", rule_key)

            if sev == "ERROR":
                st.error(
                    f"**❌ [ERROR] {rule_title}{period_badge}**\n\n"
                    f"{msg}\n\n"
                    f"*Why it matters:* {rule_info.get('why_it_matters', '')}\n\n"
                    f"*Action:* {rule_info.get('review_guidance', '')}"
                )
            elif sev == "WARN":
                st.warning(
                    f"**⚠️ [WARN] {rule_title}{period_badge}**\n\n"
                    f"{msg}\n\n"
                    f"*Why it matters:* {rule_info.get('why_it_matters', '')}\n\n"
                    f"*Review Note:* Heuristic review flag only; does not claim source data is incorrect."
                )
            elif sev == "INFO":
                st.info(
                    f"**ℹ️ [INFO] {rule_title}{period_badge}**\n\n"
                    f"{msg}\n\n"
                    f"*Context:* {rule_info.get('plain_explanation', '')}"
                )
            else:
                st.success(
                    f"**✅ [PASS] {rule_title}**\n\n"
                    f"{msg}"
                )


# =========================================================
# PAGE 4: RUN HISTORY & DIFF
# =========================================================
elif page == "📜 Run History":
    st.markdown('<div class="brand-title">📜 Run History & Snapshot Comparison</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Chronological audit log of all quality surveillance runs and side-by-side snapshot comparison.</div>',
        unsafe_allow_html=True,
    )

    # History Table
    st.subheader("Historical Ingestion Runs")
    history_rows = []
    for r in runs:
        history_rows.append(
            {
                "Run ID": r["id"],
                "Checked At (UTC)": r["checked_at"][:19].replace("T", " "),
                "Overall Status": r["status"],
                "Observations": r["observation_count"],
                "Errors": r["error_count"],
                "Warnings": r["warning_count"],
                "Series ID": r["series_id"],
            }
        )

    st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Compare Any Two Monitoring Runs")

    if len(runs) < 2:
        st.info("ℹ️ At least two quality runs are required to compare historical snapshots. Run another check from the sidebar to test comparison.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            run_a_id = st.selectbox("Baseline Run (Earlier)", options=[r["id"] for r in runs], index=min(1, len(runs) - 1))
        with c2:
            run_b_id = st.selectbox("Target Run (Later)", options=[r["id"] for r in runs], index=0)

        if run_a_id == run_b_id:
            st.info("Select two different run IDs to compare their observation snapshots.")
        else:
            data_a = get_run_details(db_url, run_a_id)
            data_b = get_run_details(db_url, run_b_id)

            if data_a and data_b:
                comp = compare_run_snapshots(data_a["observations"], data_b["observations"])
                st.write(f"**Comparison Result:** {comp['summary']}")

                if comp["diffs"]:
                    diff_table = pd.DataFrame(comp["diffs"]).rename(
                        columns={
                            "period": "Year",
                            "change_type": "Diff Classification",
                            "old_value": f"Run #{run_a_id} Value",
                            "new_value": f"Run #{run_b_id} Value",
                            "old_status": f"Run #{run_a_id} Flag",
                            "new_status": f"Run #{run_b_id} Flag",
                            "value_diff": "Net Difference",
                        }
                    )
                    st.dataframe(diff_table, use_container_width=True, hide_index=True)
                else:
                    st.success(f"Both Run #{run_a_id} and Run #{run_b_id} contain identical observations.")


# =========================================================
# PAGE 5: SOURCE AND METHODOLOGY
# =========================================================
elif page == "ℹ️ Source & Methodology":
    st.markdown('<div class="brand-title">ℹ️ Source & Methodology</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">Technical architecture, data provenance, pipeline explanation, and official scope.</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Data Provenance & Source Metadata")
    st.markdown(
        f"""
        - **Source Authority:** [Eurostat (European Commission)](https://ec.europa.eu/eurostat)
        - **Dataset Code:** `{DEFAULT_SERIES.dataset}`
        - **Indicator:** Gross domestic product at market prices (`B1GQ`)
        - **Geographic Entity:** Greece (`EL`)
        - **Accounting Standard:** European System of Accounts (ESA 2010)
        - **Valuation Unit:** Current prices, million euro (`CP_MEUR`)
        - **Reporting Frequency:** Annual (`A`)
        - **Direct API Wire Endpoint:** [`{DEFAULT_SERIES.source_url}`]({DEFAULT_SERIES.source_url})
        - **Reuse Terms:** Subject to Eurostat open data reuse policy (free reuse with attribution).
        """
    )

    st.markdown("---")
    st.subheader("Data Pipeline Architecture")
    st.markdown(
        """
        1. **HTTP Ingestion Layer (`ingestion.py`):**
           - Issues an HTTPS request to Eurostat's SDMX 2.1 TSV dissemination service with configurable timeouts.
           - Handles network timeouts, DNS errors, HTTP 4xx/5xx codes, and malformed header structures.
           - Parses tab-separated values, isolating dimension matrix keys, numeric values, Eurostat missing value markers (`:`), and observation status flags (`p`, `b`, `e`).
           - Preserves source metadata (dataset, dimensions, retrieval timestamp, URL) on each observation.
        2. **Relational Persistence Layer (`store.py`):**
           - Stores snapshots in SQLite (`GDM_DATABASE_URL`, defaulting to `data/monitor.db`).
           - Preserves distinct historical run logs in `quality_runs` and observation snapshots in `observations` with `(run_id, period)` unique constraints.
           - Records audit findings with structured JSON payloads in `quality_findings`.
        3. **Quality Evaluation Service (`quality.py`):**
           - Evaluates period validity (`1900–2100`), period uniqueness, and active series completeness.
           - Flags large YoY changes (default `> 30%`) as warnings for human review.
           - Compares current observations against historical snapshots to detect data revisions.
        4. **Interactive Dashboard & CLI:**
           - CLI: `greek-data-monitor run` and `greek-data-monitor history`.
           - Web UI: Streamlit + Plotly responsive dashboard on `localhost:8501`.
        """
    )

    st.markdown("---")
    st.subheader("Current Scope & Known Limitations")
    st.warning(
        """
        - **Single Series Prototype:** This release is focused specifically on Greece's annual GDP from Eurostat (`nama_10_gdp`). **It does not represent comprehensive coverage of all Greek public statistics.**
        - **Heuristics vs. Verified Facts:** The 30% YoY threshold is a review heuristic, not statistical proof of error. Real-world events (e.g. the 2008–2015 Greek economic crisis or the 2020 COVID-19 pandemic) cause legitimate macroeconomic swings.
        - **Eurostat Revisions:** Official national accounts undergo regular historical revisions by national authorities (ELSTAT) and Eurostat as preliminary data is finalized.
        """
    )

st.markdown("---")
st.caption(
    "Greek Public Data Quality Monitor • Eurostat Open Statistics Surveillance • "
    "Designed for reproducible statistical surveillance & revision awareness."
)
