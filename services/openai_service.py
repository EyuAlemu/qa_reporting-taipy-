import json

from openai import OpenAI

from config import ANALYSIS_TEMPERATURE, CHAT_TEMPERATURE, OPENAI_API_KEY, OPENAI_MODEL
from database.db import load_all_tables
from services.metrics_service import calculate_kpis, get_analytics_datasets


def _client(api_key=None):
    key = (api_key or OPENAI_API_KEY or "").strip()
    if not key:
        return None
    return OpenAI(api_key=key)


def _records(df, limit=25):
    if df is None or df.empty:
        return []
    return df.head(limit).fillna("").to_dict(orient="records")


def build_qa_context(data=None, row_limit=25):
    """Build compact context from metrics.db and metrics_service outputs."""
    data = data or load_all_tables()
    kpis = calculate_kpis(data)
    analytics = get_analytics_datasets(data)

    context = {
        "kpis": kpis,
        "analytics": {name: _records(df, row_limit) for name, df in analytics.items()},
        "tables": {
            name: {
                "row_count": int(len(df)),
                "columns": list(df.columns),
                "sample_rows": _records(df, min(row_limit, 10)),
            }
            for name, df in data.items()
            if name != "sqlite_sequence"
        },
    }
    return json.dumps(context, indent=2, default=str)


def _fallback_answer(question, data=None):
    data = data or load_all_tables()
    kpis = calculate_kpis(data)
    q = str(question or "").lower()

    if "total" in q and ("defect" in q or "bug" in q):
        return f"The total number of defects is {kpis.get('total_defects', 0)}."
    if "critical" in q:
        return f"There are {kpis.get('critical_defects', 0)} critical defects."
    if "high" in q:
        return f"There are {kpis.get('high_defects', 0)} high severity defects."
    if "pass" in q:
        return f"The overall pass rate is {kpis.get('pass_rate_pct', 0):.1f}%."
    if "execution" in q or "executed" in q:
        return (
            f"{kpis.get('executed_test_cases', 0)} of {kpis.get('total_test_cases', 0)} "
            f"test cases are executed, for an execution rate of {kpis.get('execution_rate_pct', 0):.1f}%."
        )
    if "coverage" in q or "scope" in q:
        return f"Scope coverage is {kpis.get('scope_coverage_pct', 0):.1f}%."
    if "deferred" in q:
        return f"There are {kpis.get('deferred_tests', 0)} deferred tests."
    if "risk" in q or "ready" in q or "release" in q:
        return (
            f"Release risk is driven by {kpis.get('critical_defects', 0)} critical defects, "
            f"{kpis.get('high_defects', 0)} high defects, and "
            f"{kpis.get('deferred_tests', 0)} deferred tests."
        )

    return (
        f"Dashboard snapshot: execution is {kpis.get('execution_rate_pct', 0):.1f}%, "
        f"pass rate is {kpis.get('pass_rate_pct', 0):.1f}%, "
        f"scope coverage is {kpis.get('scope_coverage_pct', 0):.1f}%, "
        f"and total defects are {kpis.get('total_defects', 0)}."
    )


def _fallback_analysis(data=None):
    data = data or load_all_tables()
    kpis = calculate_kpis(data)

    total_tests = kpis.get("total_test_cases", 0)
    executed = kpis.get("executed_test_cases", 0)
    execution_rate = kpis.get("execution_rate_pct", 0)
    pass_rate = kpis.get("pass_rate_pct", 0)
    coverage = kpis.get("scope_coverage_pct", 0)
    defects = kpis.get("total_defects", 0)
    closed = kpis.get("closed_defects", 0)
    deferred = kpis.get("deferred_tests", 0)
    critical = kpis.get("critical_defects", 0)
    high = kpis.get("high_defects", 0)
    medium = kpis.get("medium_defects", 0)
    low = kpis.get("low_defects", 0)

    readiness = (
        "Not ready for release"
        if critical or high or deferred
        else "Closer to release readiness"
    )

    return f"""1) Executive Summary
Total test cases: {total_tests}, with {executed} executed ({execution_rate:.1f}% execution rate).
Overall pass rate stands at {pass_rate:.1f}%.
Scope coverage is {coverage:.1f}%, with {deferred} deferred tests.
Defect count is {defects}, with {closed} closed defects.
Severity mix: Critical {critical}, High {high}, Medium {medium}, Low {low}.

2) Key Risks
Critical defects: {critical}.
High severity defects: {high}.
Deferred tests: {deferred}, which may reduce confidence in full validation.
Closed defects: {closed}, compared with {defects} total defects.

3) Strengths
Execution rate is {execution_rate:.1f}% across the loaded dashboard data.
Pass rate is {pass_rate:.1f}%.
Scope coverage is {coverage:.1f}%.
Severity and defect counts are tracked in metrics.db for prioritization.

4) Release-Readiness View
{readiness} based on the current critical/high defects and deferred tests.
Resolve critical and high defects before release approval.
Improve deferred test coverage to raise confidence.

5) Recommended Next Actions
Prioritize critical defects first, then high severity defects.
Review deferred tests and unblock the highest-risk scenarios.
Use defect root cause trends to focus engineering fixes.
Re-run the dashboard after updates to confirm execution, pass rate, and closure movement.

6) Notable Anomalies
Closed defects are {closed} while total defects are {defects}; verify resolved versus closed status alignment.
Deferred tests are {deferred}; confirm whether they are accepted scope changes or testing blockers.
"""


def _chat(messages, temperature, max_tokens, api_key=None):
    client = _client(api_key)
    if client is None:
        return None

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def analyze_qa_metrics(context=None, api_key=None):
    """Generate executive AI analysis. Kept for components.ai_panels compatibility."""
    context = context or build_qa_context()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior QA Director. Analyze only the supplied QA dashboard data. "
                "Be concise, numeric, and do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create sections: Executive Summary, Key Risks, Strengths, "
                "Release-Readiness View, Recommended Next Actions, Notable Anomalies.\n\n"
                f"QA context:\n{str(context)[:12000]}"
            ),
        },
    ]

    try:
        answer = _chat(messages, ANALYSIS_TEMPERATURE, 900, api_key)
        if answer:
            return answer
    except Exception as exc:
        return _fallback_analysis()

    return _fallback_analysis()


def qa_chatbot(question, context=None, api_key=None):
    """Answer dashboard questions. Kept for components.ai_panels/sidebar compatibility."""
    question = str(question or "").strip()
    if not question:
        return "Ask a question about defects, pass rate, execution, risks, or readiness."

    context = context or build_qa_context()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a QA dashboard assistant. Answer only from the provided data. "
                "If the data does not answer the question, say so."
            ),
        },
        {"role": "user", "content": f"QA context:\n{str(context)[:12000]}"},
        {"role": "user", "content": question},
    ]

    try:
        answer = _chat(messages, CHAT_TEMPERATURE, 600, api_key)
        if answer:
            return answer
    except Exception:
        pass

    return _fallback_answer(question)


def ask_openai(question, api_key=None):
    return qa_chatbot(question, api_key=api_key)


def is_openai_configured(api_key=None):
    return bool((api_key or OPENAI_API_KEY or "").strip())


def generate_program_analysis(dataset=None, api_key=None):
    context = build_qa_context() if dataset is None else json.dumps(dataset, indent=2, default=str)
    return analyze_qa_metrics(context, api_key=api_key)


def ask_dashboard_chat(user_question, dataset=None, history=None, api_key=None):
    context = build_qa_context() if dataset is None else json.dumps(dataset, indent=2, default=str)
    return qa_chatbot(user_question, context=context, api_key=api_key)
