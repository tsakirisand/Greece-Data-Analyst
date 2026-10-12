# Greek Public Data Quality Monitor

A reliable, reproducible data quality monitoring tool for official public statistics about Greece. The first supported series is Greece’s annual Gross Domestic Product (GDP) from Eurostat.

The monitor validates each observation against quality rules, captures complete historical snapshots, tracks revisions across runs, and persists structured findings in a local SQLite database.

---

## Supported Series & Source Attribution

- **Dataset:** `nama_10_gdp` (*Gross domestic product at market prices*)
- **Geography (`geo`):** `EL` (Greece)
- **National accounts item (`na_item`):** `B1GQ` (Gross domestic product at market prices)
- **Unit (`unit`):** `CP_MEUR` (Current prices, million euro)
- **Frequency (`freq`):** `A` (Annual)
- **Source API:** Eurostat Dissemination API (SDMX 2.1 TSV)
- **Direct Source URL:** [`https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.EL?format=TSV`](https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.EL?format=TSV)
- **License / Reuse:** Eurostat open data reuse policy applies to source statistics.

### Verified Facts vs. Review Heuristics

- **Verified Facts:**
  - Eurostat's ESA 2010 national accounts time series for Greek annual GDP in current prices covers 1995 to the present.
  - Earlier matrix columns (1975–1994) in the disseminated dataset contain missing value markers (`:`) representing periods before ESA 2010 coverage.
  - Recent years (e.g., 2023, 2024, 2025) carry observation status flags such as `p` (provisional) or `b` (break in series).
- **Review Heuristics:**
  - The year-over-year percentage change threshold (default ±30%) is a heuristic flag for review, **not an assertion that official data is erroneous**. Major macroeconomic events (e.g., the 2008–2015 debt crisis or the 2020 COVID-19 pandemic) and statistical benchmark revisions can generate substantial changes. Large changes trigger a `WARN` finding without causing the run to fail.

---

## Installation & Setup

Requires Python 3.11+.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install package and dependencies in editable mode
pip install -e .

# Optional: Install test dependencies
pip install -e ".[test]"
```

Both `greek-data-monitor` and the shorthand alias `gdm` are registered CLI commands.

---

## Usage

### 1. Run Quality Monitor via CLI

Fetch the series, run quality checks, compare against previous snapshots for revisions, record the run in SQLite, and print a formatted summary:

```bash
greek-data-monitor run
# or using the shorthand:
gdm run
```

### 2. Launch Interactive Web Dashboard

To explore the data, visual charts, quality findings, and historical revisions in your browser:

```bash
streamlit run app.py
```

The web dashboard is available at:
👉 **[http://localhost:8501](http://localhost:8501)**

The dashboard includes 5 comprehensive sections:
1. **📌 Overview:**
   - **Audit Status Banner:** Immediate visual status (`PASS`, `WARN`, `FAIL`) for the active run snapshot.
   - **KPI Cards:** Latest observed GDP, latest YoY growth percentage, total observations, and retrieval timestamp.
   - **Time-Series Visualization:** Interactive Plotly GDP trajectory (1995–2025) highlighting provisional (`p`) observation diamonds and tooltips.
   - **"What Changed?" Section:** Automated delta analysis comparing the current run against the preceding historical run (identifying value revisions, added periods, or status flag transitions).
2. **🔍 Data Explorer:**
   - **Interactive Observation Table:** Displays Year, GDP (Million EUR), Data Status label, Status Flag (`p`, `b`, `:`), Flag Meaning, Unit, and Retrieval Timestamp.
   - **Filters:** Dynamic year range slider, observation status filter (*All*, *Numeric only*, *Missing values only*, *Provisional only*, *Flagged only*), text search, and column sorting.
   - **CSV Export:** One-click download button to export the currently filtered observations as a CSV file.
3. **🛡️ Quality Checks:**
   - **Findings by Severity:** Visual breakdown of findings by severity (`ERROR`, `WARN`, `INFO`, `PASS`) with rule names and affected periods.
   - **Plain-Language Explanations:** Explains what each rule checks, why it matters, and review guidance.
   - **Review Flags vs. Errors:** Clearly explains that large YoY swings trigger review warnings (`WARN`), not rejections of official data.
4. **📜 Run History & Snapshot Comparison:**
   - **Audit Log:** Chronological table of all recorded quality surveillance runs with timestamps, status, observation counts, errors, and warnings.
   - **Snapshot Comparator:** Allows users to select any baseline Run A and target Run B to inspect a side-by-side diff table highlighting revised, added, or removed values.
5. **ℹ️ Source & Methodology:**
   - **Data Provenance:** Dataset code (`nama_10_gdp`), geography (`EL`), item (`B1GQ`), unit (`CP_MEUR`), frequency (`A`), direct API URL, and reuse attribution.
   - **Pipeline Explanation:** Explains the end-to-end flow from Eurostat's SDMX 2.1 API to TSV parsing, SQLite persistence, quality checks, and dashboard presentation.
   - **Eurostat Flags Glossary:** Plain-language definitions for `:`, `p`, `b`, `e`, `u`, `c`.
   - **Scope & Limitations:** Explicitly documents that this prototype monitors one series and does not claim comprehensive Greek public-data coverage.

#### Command Options

```text
greek-data-monitor run [OPTIONS]

Options:
  --db-url TEXT       Database connection URL (default: $GDM_DATABASE_URL or sqlite:///./data/monitor.db)
  --threshold FLOAT   Year-over-year percentage change warning threshold (default: 30.0)
  --min-year INT      Minimum active series coverage year (default: 1995, or 'none')
  --timeout INT       HTTP request timeout in seconds (default: 30)
```

#### Exit Codes

- `0`: Ingestion succeeded and quality checks passed (or produced only review `WARN` / `INFO` findings).
- `1`: Ingestion failure (network timeout, HTTP error, or malformed response).
- `2`: Quality check error (`ERROR` severity findings detected, such as missing data in active range, invalid period, or duplicate periods).

### 2. Inspect Run History

View recent runs, check summary metrics, and inspect specific findings:

```bash
# List recent runs
greek-data-monitor history
# or
gdm history --limit 5

# Inspect full details and findings of a specific run
gdm history --run-id 1
```

---

## Quality Rules

| Rule Name | Severity | Description |
|---|---|---|
| `valid_period` | `ERROR` | Ensures all observations have a plausible 4-digit calendar year (1900–2100). |
| `unique_period` | `ERROR` | Verifies that no period appears more than once in the fetched series. |
| `not_null` | `ERROR` | Flags missing or unparseable numeric values within the active series coverage (≥ 1995). |
| `pre_series_coverage` | `INFO` | Explains missing values for historical periods (1975–1994) prior to ESA 2010 coverage. |
| `year_over_year_change` | `WARN` | Flags year-over-year percentage changes exceeding the threshold (default ±30%) for review. Does not fail the run. |
| `data_revision` | `WARN` | Detects when a newly fetched historical observation differs in value from the prior snapshot. |
| `status_revision` | `INFO` | Tracks when observation status flags change (e.g. from provisional `p` to finalized). |
| `all_rules` | `PASS` | Emitted when all observations satisfy configured quality checks. |

---

## Persistence & Database Schema

The database path is configurable via the `GDM_DATABASE_URL` environment variable or the `--db-url` command-line option:

```bash
export GDM_DATABASE_URL="sqlite:///./data/monitor.db"
```

The database stores:

1. **`series_metadata`**: Dataset identifier, dimension parameters, units, source URLs, and update timestamps.
2. **`quality_runs`**: Chronological run audit log with run ID, checked timestamp (ISO 8601 UTC), observation count, run status (`PASS`/`WARN`/`FAIL`), and counts of errors and warnings.
3. **`observations`**: Snapshot of every observation fetched per run, with `(run_id, period)` unique constraint, value, status flag, raw string, and retrieval timestamp.
4. **`quality_findings`**: Structured findings linked to each run by `run_id`, including rule name, severity, affected period, message, and structured JSON details.

---

## Testing

The test suite runs completely offline using local fixtures and mocks, requiring no network access:

```bash
python3 -m pytest -v
```

Tests cover:
- TSV matrix and row-based parsing with missing markers (`:`, `: u`, `: c`) and flags (`p`, `b`, `e`).
- HTTP error handling, connection failures, timeouts, and non-200 responses.
- Quality rules evaluation, threshold boundaries, and revision detection.
- SQLite persistence, schema initialization, and historical snapshot queries.
- CLI argument parsing, execution paths, and status code verification.

---

## Current Scope & Limitations

1. **Single Series Prototype:** Currently monitors Eurostat Greek GDP (`nama_10_gdp`, `geo=EL`, `B1GQ`, `CP_MEUR`). Ingestion architecture is structured via `SeriesConfig` to accommodate additional Eurostat datasets and other Greek data sources (e.g., ELSTAT).
2. **Network Dependency for Live Runs:** Live executions require internet access to Eurostat's dissemination servers.
3. **Storage:** Standard SQLite local persistence.
