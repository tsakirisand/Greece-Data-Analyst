from __future__ import annotations

import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from greek_data_monitor.config import DEFAULT_SERIES, Settings
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

# Custom CSS for polished interface
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
    }
    .badge-pass { background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-warn { background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-error { background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-info { background-color: #e0f2fe; color: #075985; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = Settings()

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")
db_url = st.sidebar.text_input("Database URL", value=settings.database_url)
yoy_threshold = st.sidebar.slider(
    "YoY Change Warning Threshold (%)",
    min_value=5.0,
    max_value=60.0,
    value=settings.max_abs_yoy_change_pct,
    step=1.0,
    help="Flags year-over-year percentage swings above this threshold for review.",
)
min_year = st.sidebar.number_input(
    "Series Coverage Start Year",
    min_value=1950,
    max_value=2030,
    value=settings.min_year if settings.min_year else 1995,
    help="Eurostat ESA 2010 GDP coverage for Greece begins in 1995.",
)

# Trigger manual run from UI
st.sidebar.markdown("---")
if st.sidebar.button("🚀 Fetch & Run Quality Check", use_container_width=True, type="primary"):
    with st.spinner("Fetching latest Eurostat GDP feed and executing quality rules..."):
        try:
            prev_obs = get_latest_observations(db_url, DEFAULT_SERIES.series_id)
            new_obs = fetch_eurostat_series(DEFAULT_SERIES, timeout=settings.request_timeout_seconds)
            findings = inspect(
                new_obs,
                threshold_pct=yoy_threshold,
                previous_observations=prev_obs,
                min_year=int(min_year),
            )
            new_run_id = save_run(
                database_url=db_url,
                observations=new_obs,
                findings=findings,
                series_id=DEFAULT_SERIES.series_id,
            )
            st.sidebar.success(f"Successfully recorded Run #{new_run_id}!")
            st.rerun()
        except IngestionError as exc:
            st.sidebar.error(f"Ingestion failed: {exc}")
        except Exception as exc:
            st.sidebar.error(f"Failed: {exc}")

# Header
st.markdown('<div class="main-header">🇬🇷 Greek Public Data Quality Monitor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Automated statistical validation, historical snapshots, and revision tracking for official Greek public data.</div>',
    unsafe_allow_html=True,
)

# Metadata banner
st.info(
    f"**Source Series:** Eurostat Dissemination API • **Dataset:** `{DEFAULT_SERIES.dataset}` • "
    f"**Geography:** Greece (`EL`) • **National Accounts Item:** `{DEFAULT_SERIES.dimensions.get('na_item')}` (GDP at market prices) • "
    f"**Unit:** `{DEFAULT_SERIES.unit}` (Current prices, million euro)"
)

# Retrieve historical runs
runs = list_runs(db_url, limit=20)

if not runs:
    st.warning("No quality runs found in the database. Click **'Fetch & Run Quality Check'** in the sidebar to perform the first live ingestion.")
    st.stop()

# Run Selector
run_options = {
    f"Run #{r['id']} — {r['checked_at'][:19]} ({r['status']})": r["id"]
    for r in runs
}
selected_label = st.selectbox("Select Quality Run Snapshot to Inspect", options=list(run_options.keys()))
selected_run_id = run_options[selected_label]

run_data = get_run_details(db_url, selected_run_id)
if not run_data:
    st.error(f"Could not load details for Run #{selected_run_id}")
    st.stop()

current_run = run_data["run"]
observations = run_data["observations"]
findings = run_data["findings"]

# Extract numeric observations for visualization
df_obs = pd.DataFrame(observations)
if not df_obs.empty and "value" in df_obs.columns:
    df_obs["period"] = pd.to_numeric(df_obs["period"])
    df_obs["value"] = pd.to_numeric(df_obs["value"])
    df_numeric = df_obs.dropna(subset=["value"]).sort_values("period").reset_index(drop=True)
    df_numeric["yoy_change_pct"] = df_numeric["value"].pct_change() * 100.0
else:
    df_numeric = pd.DataFrame()

# Top KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_label = current_run["status"]
    if status_label == "PASS":
        badge = '<span class="badge-pass">PASS</span>'
    elif status_label == "WARN":
        badge = '<span class="badge-warn">WARNING</span>'
    else:
        badge = '<span class="badge-error">FAIL</span>'
    st.metric("Quality Status", status_label, help="Overall status of this quality audit run")
    st.markdown(f"Status: {badge}", unsafe_allow_html=True)

with col2:
    if not df_numeric.empty:
        latest_row = df_numeric.iloc[-1]
        latest_val = latest_row["value"]
        latest_yr = int(latest_row["period"])
        flag_str = f" ({latest_row['source_status']})" if latest_row.get("source_status") else ""
        st.metric(f"Latest GDP ({latest_yr})", f"€{latest_val:,.1f} M{flag_str}")
    else:
        st.metric("Latest GDP", "N/A")

with col3:
    if not df_numeric.empty and len(df_numeric) > 1:
        latest_yoy = df_numeric.iloc[-1]["yoy_change_pct"]
        st.metric("Latest YoY Growth", f"{latest_yoy:+.2f}%")
    else:
        st.metric("Latest YoY Growth", "N/A")

with col4:
    err_count = current_run["error_count"]
    warn_count = current_run["warning_count"]
    st.metric("Findings Summary", f"{err_count} Errors / {warn_count} Warns", delta=f"{len(findings)} total findings")

st.markdown("---")

# Visualizations
tab_charts, tab_findings, tab_raw = st.tabs(["📊 Time Series & YoY Analytics", "📋 Quality Findings", "💾 Raw Observations"])

with tab_charts:
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        if not df_numeric.empty:
            fig_gdp = px.line(
                df_numeric,
                x="period",
                y="value",
                markers=True,
                title="Greece Annual GDP (Eurostat nama_10_gdp)",
                labels={"period": "Year", "value": "GDP (Current Million EUR)"},
                hover_data=["source_status", "raw_value"],
            )
            fig_gdp.update_traces(
                line_color="#0284c7",
                marker=dict(size=7, color="#0369a1"),
                hovertemplate="<b>Year %{x}</b><br>GDP: €%{y:,.1f} M<br>Status: %{customdata[0]}<extra></extra>",
            )
            fig_gdp.update_layout(template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig_gdp, use_container_width=True)
        else:
            st.info("No numeric observations to display in chart.")

    with col_chart2:
        if not df_numeric.empty and len(df_numeric) > 1:
            df_yoy = df_numeric.dropna(subset=["yoy_change_pct"]).copy()
            df_yoy["is_exceeded"] = df_yoy["yoy_change_pct"].abs() > yoy_threshold

            fig_yoy = go.Figure()
            fig_yoy.add_trace(
                go.Bar(
                    x=df_yoy["period"],
                    y=df_yoy["yoy_change_pct"],
                    marker_color=df_yoy["is_exceeded"].map({True: "#ea580c", False: "#38bdf8"}),
                    name="YoY Growth %",
                    hovertemplate="<b>Year %{x}</b><br>YoY Change: %{y:+.2f}%<extra></extra>",
                )
            )
            fig_yoy.add_hline(
                y=yoy_threshold,
                line_dash="dash",
                line_color="#dc2626",
                annotation_text=f"+{yoy_threshold:.0f}% Warning Threshold",
            )
            fig_yoy.add_hline(
                y=-yoy_threshold,
                line_dash="dash",
                line_color="#dc2626",
                annotation_text=f"-{yoy_threshold:.0f}% Warning Threshold",
            )
            fig_yoy.update_layout(
                title=f"Year-over-Year Growth Rate & Threshold (±{yoy_threshold:.0f}%)",
                xaxis_title="Year",
                yaxis_title="YoY Change (%)",
                template="plotly_white",
            )
            st.plotly_chart(fig_yoy, use_container_width=True)
        else:
            st.info("Insufficient data for YoY growth calculation.")

with tab_findings:
    st.subheader(f"Findings for Run #{selected_run_id}")
    if findings:
        for f in findings:
            sev = f["severity"]
            period_str = f" [Period {f['period']}]" if f["period"] else ""
            rule_str = f["rule"]
            msg = f["message"]

            if sev == "PASS":
                st.success(f"**[{sev}] {rule_str}{period_str}:** {msg}")
            elif sev == "INFO":
                st.info(f"**[{sev}] {rule_str}{period_str}:** {msg}")
            elif sev == "WARN":
                st.warning(f"**[{sev}] {rule_str}{period_str}:** {msg}")
            else:
                st.error(f"**[{sev}] {rule_str}{period_str}:** {msg}")
    else:
        st.write("No findings recorded for this run.")

with tab_raw:
    st.subheader("Observations Snapshot Table")
    if not df_obs.empty:
        display_cols = ["period", "value", "source_status", "raw_value", "fetched_at"]
        existing_cols = [c for c in display_cols if c in df_obs.columns]
        st.dataframe(df_obs[existing_cols], use_container_width=True, hide_index=True)

        csv_buffer = io.StringIO()
        df_obs.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Snapshot as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"greek_gdp_snapshot_run_{selected_run_id}.csv",
            mime="text/csv",
        )
    else:
        st.write("No observations found in this snapshot.")

st.markdown("---")
st.caption(
    "Greek Public Data Quality Monitor • Eurostat Open Data Dissemination • "
    "Designed for reproducible statistical surveillance & revision awareness."
)
