# AMPCUS QA Reporting Dashboard

Taipy GUI application for QA reporting, test execution tracking, defect analytics, data management, and AI-assisted release insights.

The app reads QA metrics from `database/metrics.db`, calculates dashboard KPIs with pandas, renders the dashboard in Taipy, and can use OpenAI for deeper analysis when an API key is configured.

## Features

- Executive Overview with KPI cards, scope coverage, defect summaries, root causes, active alerts, and release-readiness signals.
- Test Execution page with cycle-level execution, pass rate, planned/executed counts, blocked tests, and deferred tests.
- Defect Analytics page with severity by cycle, error discovery trend, defect status by priority, root cause distribution, and defect records.
- Data Management page for reviewing current data and adding test cycles or defects.
- AI Analysis page that generates a release-style QA analysis from the current dashboard context.
- Insight Bot page for asking questions about the loaded QA data.
- Sidebar Insight Bot with quick dashboard answers from the same SQLite data.
- SQLite database backend stored in `database/metrics.db`.
- OpenAI integration with deterministic fallback answers when `OPENAI_API_KEY` is missing or the API call fails.

## Quick Start

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Optional: set an OpenAI API key for AI-generated responses:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

3. Run the app:

```powershell
python app.py
```

4. Open the URL printed in the terminal. The app starts on the first available local port from `5000` through `5049`, for example:

```text
http://127.0.0.1:5000/executive-overview
```

## Pages

- `Executive Overview`: high-level QA dashboard with KPIs, charts, alerts, and release readiness.
- `Test Execution`: execution progress and pass-rate analysis by test cycle.
- `Defect Analytics`: defect trends, severity/cycle analysis, status analysis, root causes, and defect table.
- `Data Management`: add test cycles, add defects, and review current `test_execution` and `defects` data.
- `AI Insights & Chat`: generate AI analysis and ask the main Insight Bot dashboard questions.

The app also keeps route aliases for `home` and `data-explorer`.

## AI Behavior

AI logic lives in `services/openai_service.py`.

- `build_qa_context()` builds compact JSON context from the SQLite tables, KPIs, and analytics datasets.
- `analyze_qa_metrics()` creates the AI Analysis output.
- `qa_chatbot()` answers dashboard questions for the main Insight Bot and compatibility helpers.
- The Generate AI Analysis button runs as a long callback and shows a loading state while analysis is being generated.
- If OpenAI is not configured or the request fails, the app logs the failure and returns local fallback analysis from the dashboard data.

Useful questions:

- `Which cycle is riskiest?`
- `Why is pass rate low?`
- `Which root cause has the most defects?`
- `How many critical defects are open?`
- `What actions should the team take this week?`
- `Is this release ready?`

## Data Management Rules

The Data Management page writes to SQLite without changing the dashboard logic. It validates input before saving.

Test cycle validation:

- Cycle name is required.
- Planned test cases must be greater than `0`.
- Executed, passed, failed, blocked, and deferred counts cannot be negative.
- Scope executed and scope pending must each be between `0` and `100`.
- Scope executed plus scope pending must total `100`.
- Executed test cases cannot be greater than planned test cases.
- Passed, failed, and blocked counts cannot exceed executed test cases.
- Deferred test cases cannot exceed not-executed test cases.

Defect validation:

- Defect ID is required.
- Cycle is required.
- Duplicate defect IDs are blocked and shown as a warning.

## Database

The app uses SQLite:

```text
database/metrics.db
```

The primary dashboard tables are:

- `test_execution`
- `defects`

Other tables are discovered dynamically and can be included in AI context. Database helpers live in `database/db.py`, and metric calculations live in `services/metrics_service.py`.

## Configuration

Configuration is in `config.py`:

- `APP_TITLE`
- `DB_PATH`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `ANALYSIS_TEMPERATURE`
- `CHAT_TEMPERATURE`

Current OpenAI model:

```text
gpt-4o-mini
```

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- requirements.txt
|-- README.md
|-- check_db.py
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

## Development Notes

- Restart the app after Python changes.
- Hard refresh the browser if old CSS or old page content is still visible.
- `app.py` removes local `__pycache__` folders on startup.
- `.gitignore` excludes Python cache files, virtual environments, `.env`, and log files.
- Do not commit your OpenAI API key.

Useful syntax check:

```powershell
$files = Get-ChildItem -Recurse -File -Filter *.py | ForEach-Object { $_.FullName }
python -m py_compile @files
```

If Python cache files were already tracked by Git, remove them from Git tracking after closing any app process that may be using them:

```powershell
git rm -r --cached __pycache__ components/__pycache__ database/__pycache__ pages/__pycache__ services/__pycache__
git add .gitignore
git commit -m "Ignore generated Python cache files"
```

To push the current branch named `master`:

```powershell
git push -u origin master
```
