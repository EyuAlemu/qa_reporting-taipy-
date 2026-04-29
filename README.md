# AMPCUS QA Reporting Dashboard

Taipy GUI application for QA reporting, test execution tracking, defect analytics, data management, and AI-assisted release insights.

The app reads QA data from `database/metrics.db`, calculates dashboard metrics with pandas, and renders a Streamlit-like QA dashboard experience in Taipy.

## Features

- Executive Overview with KPI summary, scope coverage, error discovery rate, defect charts, root causes, and alerts.
- Test Execution page with cycle-level execution and pass-rate views.
- Defect Analytics page with severity/cycle breakdowns and discovery trends.
- Data Management page for viewing current tables and adding test cycles or defects.
- AI Analysis & Chat page for generated QA analysis and dashboard questions.
- Sidebar Insight Bot with quick metric-based answers for defects, pass rate, execution, coverage, deferred tests, and release risk.
- SQLite-backed metrics through `database/metrics.db`.
- OpenAI integration when `OPENAI_API_KEY` is configured, with metric-based fallback answers when it is not.

## Quick Start

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Optional: set an OpenAI API key for AI-generated responses:

```powershell
set OPENAI_API_KEY=your_api_key_here
```

3. Run the app:

```powershell
python app.py
```

4. Open the URL printed in the terminal. The app starts at the first available port from `5000`, for example:

```text
http://127.0.0.1:5000/executive-overview
```

## Pages

- `Executive Overview`: high-level program dashboard, defect stats, scope coverage, alerts, and readiness signals.
- `Test Execution`: test execution charts and execution data.
- `Defect Analytics`: defect severity, cycle, trend, and root-cause views.
- `Data Management`: add test cycles, add defects, and review current database records.
- `AI Insights & Chat`: generate AI analysis and ask dashboard questions.

## AI Behavior

The OpenAI service is implemented in `services/openai_service.py`.

- `analyze_qa_metrics()` generates the executive QA analysis.
- `qa_chatbot()` answers dashboard questions.
- If `OPENAI_API_KEY` is missing or the API call fails, the app returns deterministic answers from `metrics.db` instead of crashing.

Example questions:

- `How many total defects?`
- `What is the pass rate?`
- `How many critical defects?`
- `What is the execution rate?`
- `Is this release ready?`

## Database

The app uses SQLite:

```text
database/metrics.db
```

Core tables currently used:

- `test_execution`
- `defects`

Database helpers live in `database/db.py`.
Metric calculations and analytics datasets live in `services/metrics_service.py`.

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- requirements.txt
|-- README.md
|-- database/
|   |-- db.py
|   `-- metrics.db
|-- services/
|   |-- metrics_service.py
|   `-- openai_service.py
|-- components/
|   |-- ai_panels.py
|   |-- charts.py
|   |-- kpi_cards.py
|   `-- layout.py
`-- pages/
    |-- ai_chat.py
    |-- data_explorer.py
    |-- defect_analytics.py
    |-- executive_overview.py
    `-- test_execution.py
```

## Configuration

Configuration is in `config.py`:

- `APP_TITLE`
- `DB_PATH`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `ANALYSIS_TEMPERATURE`
- `CHAT_TEMPERATURE`

## Requirements

See `requirements.txt`.

Main dependencies:

- Taipy
- pandas
- plotly
- openai

## Notes

- Restart the app after code changes.
- Hard refresh the browser if old UI is still visible.
- The port is selected automatically starting at `5000`.
- The dashboard is designed around the existing `metrics.db` data and does not require sample-data generation.
