import html
import json

from taipy.gui import invoke_long_callback, notify

from components.layout import sidebar_html
from database.db import load_all_tables
from services.metrics_service import calculate_kpis
from services.openai_service import analyze_qa_metrics, build_qa_context, qa_chatbot


def _load_data():
    try:
        return load_all_tables()
    except Exception:
        return {}


def _pct(value):
    return f"{float(value or 0):.1f}%"


def _snapshot(data):
    try:
        kpis = calculate_kpis(data)
    except Exception:
        kpis = {}

    return {
        "total_test_cases": kpis.get("total_test_cases", 0),
        "executed_test_cases": kpis.get("executed_test_cases", 0),
        "pass_rate_pct": round(kpis.get("pass_rate_pct", 0), 1),
        "execution_rate_pct": round(kpis.get("execution_rate_pct", 0), 1),
        "error_discovery_rate_pct": round(kpis.get("error_discovery_rate_pct", 0), 1),
        "scope_coverage_pct": round(kpis.get("scope_coverage_pct", 0), 1),
        "total_defects": kpis.get("total_defects", 0),
        "closed_defects": kpis.get("closed_defects", 0),
        "deferred_tests": kpis.get("deferred_tests", 0),
        "severity_critical": kpis.get("critical_defects", 0),
        "severity_high": kpis.get("high_defects", 0),
        "severity_low": kpis.get("low_defects", 0),
        "severity_medium": kpis.get("medium_defects", 0),
    }


data = _load_data()
analysis_snapshot = _snapshot(data)
snapshot_json = json.dumps(analysis_snapshot, indent=2)
analysis_output = (
    "AI analysis is ready. Provide an OpenAI API key in the sidebar, "
    "then click Generate AI Analysis."
)
analysis_loading = False
analysis_status_text = ""
chat_question = ""
chat_history = ""
show_analysis = True
show_insight = False
analysis_tab_class = "ai-tab active"
insight_tab_class = "ai-tab"


def _current_context():
    return build_qa_context(_load_data())


try:
    generated_analysis_output = analyze_qa_metrics(_current_context())
except Exception as exc:
    generated_analysis_output = f"Error generating analysis: {exc}"

def _notify(state, level, message):
    try:
        notify(state, level, message)
    except Exception:
        pass


def _generate_analysis_worker(context):
    return analyze_qa_metrics(context)


def _analysis_finished(state, status, result=None):
    state.analysis_loading = False
    state.analysis_status_text = ""

    if status:
        state.analysis_output = result or "AI analysis completed, but no output was returned."
        _notify(state, "success", "AI analysis generated.")
    else:
        state.analysis_output = f"Error generating analysis: {result}"
        _notify(state, "error", "AI analysis failed.")


def generate_analysis(state):
    try:
        state.analysis_loading = True
        state.analysis_status_text = "Generating AI analysis..."
        state.analysis_output = ""
        invoke_long_callback(
            state,
            _generate_analysis_worker,
            [_current_context()],
            _analysis_finished,
        )
    except Exception as exc:
        state.analysis_loading = False
        state.analysis_status_text = ""
        state.analysis_output = f"Error generating analysis: {exc}"
        _notify(state, "error", "AI analysis failed.")


def ask_question(state):
    question = str(state.chat_question or "").strip()
    if not question:
        _notify(state, "warning", "Type a question first.")
        return

    try:
        answer = qa_chatbot(question, context=_current_context())
    except Exception as exc:
        answer = f"Error answering question: {exc}"

    state.chat_history = (
        f"{state.chat_history}\n\n"
        f"**You:** {question}\n\n"
        f"**Insight Bot:** {answer}"
    ).strip()
    state.chat_question = ""


def clear_chat(state):
    state.chat_history = ""
    state.chat_question = ""


def open_ai_analysis(state):
    state.show_analysis = True
    state.show_insight = False
    state.analysis_tab_class = "ai-tab active"
    state.insight_tab_class = "ai-tab"


def open_insight_bot(state):
    state.show_analysis = False
    state.show_insight = True
    state.analysis_tab_class = "ai-tab"
    state.insight_tab_class = "ai-tab active"


page_body = f"""
<style>
.dashboard-shell {{ display:grid; grid-template-columns:306px minmax(0,1fr); background:#ffffff; color:#111827; min-height:100vh; }}
.sidebar-shell {{ display:flex; flex-direction:column; background:#f0f2f6; padding:54px 25px 18px 12px; min-height:100vh; }}
.nav-menu {{ display:grid; gap:8px; }}
.nav-form {{ margin:0; padding:0; width:100%; }}
.nav-link {{ display:grid; grid-template-columns:22px minmax(0,1fr); align-items:center; column-gap:9px; width:100%; min-height:34px; padding:6px 12px; border:0; border-radius:9px; color:#34405a; text-align:left; text-decoration:none; font-family:inherit; font-size:0.98rem; line-height:1.32; background:transparent; box-shadow:none; cursor:pointer; }}
.nav-link, .nav-form, .nav-form button, .nav-link:visited, .nav-link:hover, .nav-link:active, .nav-link:focus, .nav-link .nav-label, .nav-link:visited .nav-label, .nav-link:hover .nav-label, .nav-link * {{ color:#34405a !important; -webkit-text-fill-color:#34405a !important; text-decoration:none !important; }}
.nav-link:hover {{ background:#e4e8f0; box-shadow:none; }}
.nav-link.nav-active, .nav-form .nav-link.nav-active, .nav-form .nav-link.nav-active *, .nav-link.nav-active:visited, .nav-link.nav-active:hover, .nav-link.nav-active .nav-label, .nav-link.nav-active:visited .nav-label, .nav-link.nav-active:hover .nav-label, .nav-link.nav-active * {{ color:#2563eb !important; -webkit-text-fill-color:#2563eb !important; text-decoration:none !important; font-weight:800 !important; }}
.nav-link.nav-active {{ background:#dbeafe; color:#2563eb; font-weight:800; }}
.nav-icon {{ display:inline-grid; place-items:center; width:22px; font-size:1.08rem; line-height:1; }}
.nav-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.sidebar-rule {{ height:1px; background:#c5cad3; margin:20px 0 20px 0; }}
.sidebar-rule.compact {{ margin:18px 0 18px 0; }}
.copyright {{ color:#8b919c; font-size:0.98rem; line-height:1.7; margin:4px 0 18px 0; }}
.sidebar-footer {{ margin-top:0; color:#172033; font-size:0.98rem; line-height:1.5; }}
.bot-title {{ display:flex; align-items:center; gap:6px; color:#172033; font-weight:800; font-size:1.16rem; margin-bottom:14px; }}
.bot-title-icon {{ font-size:0.95rem; }}
.bot-card {{ border:1px solid #c7ccd6; border-radius:9px; padding:18px 18px 16px 18px; background:#f8f9fb; }}
.bot-copy {{ margin-bottom:8px; color:#172033; }}
.sidebar-chat-display {{ display:grid; gap:8px; max-height:190px; overflow:auto; margin:8px 0 10px 0; color:#172033; font-size:0.9rem; }}
.sidebar-chat-msg {{ padding:8px 10px; border-radius:8px; background:#ffffff; border:1px solid #e1e5ec; overflow-wrap:anywhere; }}
.sidebar-chat-user {{ background:#eef2ff; }}
.sidebar-chat-bot {{ background:#fff7ed; }}
.sidebar-bot-input {{ width:100%; height:48px; border:0; border-radius:10px; background:#ffffff; margin:8px 0 18px 0; padding:0 12px; color:#172033; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.8); }}
.sidebar-bot-btn {{ width:100%; height:49px; border-radius:9px; font-size:1.04rem; cursor:pointer; border:0; background:#2563eb; color:#ffffff; font-weight:700; }}
.sidebar-bot-btn:disabled {{ opacity:0.72; cursor:wait; }}
.sidebar-bot-clear-btn {{ margin-top:16px; border:1px solid #c7ccd6; background:#ffffff; color:#172033; }}
.main-shell {{ display:grid; gap:24px; align-content:start; padding:86px 66px 26px 100px; min-width:0; }}
.page-header {{ display:grid; gap:10px; justify-items:center; text-align:center; }}
.logo-shell {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
.logo-text {{ font-size:3.35rem; font-weight:500; letter-spacing:-0.06em; color:#1681bd; font-family:Georgia, 'Times New Roman', serif; }}
.logo-subtext {{ font-size:1.4rem; color:#4b5563; letter-spacing:0; }}
.ai-page {{
  display: grid;
  gap: 22px;
  max-width: 1280px;
}}
.ai-header {{
  justify-items: center;
  gap: 10px;
  margin-top: -16px;
  margin-bottom: 24px;
}}
.ai-header .logo-text {{
  font-size: 3.85rem;
}}
.ai-header .logo-subtext {{
  font-size: 1.35rem;
}}
.ai-title {{
  margin: 0;
  color: #172033;
  font-size: 2.45rem;
  font-weight: 800;
}}
.ai-subtitle {{
  margin: 0 0 12px 0;
  color: #8b919c;
  font-size: 1rem;
}}
.ai-tabs {{
  display: flex;
  gap: 24px;
  border-bottom: 1px solid #e5e7eb;
  min-height: 42px;
  align-items: end;
}}
.ai-tab {{
  border: 0;
  background: transparent;
  color: #172033 !important;
  -webkit-text-fill-color: #172033 !important;
  padding: 0 0 13px 0;
  font-size: 0.98rem;
  cursor: pointer;
  box-shadow: none;
  min-width: auto;
  text-decoration: none !important;
}}
.ai-tab:link,
.ai-tab:visited,
.ai-tab:hover,
.ai-tab:active,
.ai-tab:focus {{
  color: #172033 !important;
  -webkit-text-fill-color: #172033 !important;
  text-decoration: none !important;
}}
.ai-tab.active {{
  color: #2563eb !important;
  -webkit-text-fill-color: #2563eb !important;
  border-bottom: 2px solid #2563eb;
}}
.ai-analysis-section {{
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  gap: 62px;
  align-items: start;
  margin-bottom: 28px;
}}
.ai-analysis-inputs h2,
.ai-latest-output h2,
.insight-section h2 {{
  margin: 0 0 20px 0;
  color: #172033;
  font-size: 1.85rem;
  font-weight: 800;
}}
.ai-analysis-inputs p,
.insight-section p {{
  margin: 0 0 22px 0;
  color: #34405a;
  font-size: 1rem;
  line-height: 1.55;
}}
.ai-json-details {{
  margin-bottom: 20px;
}}
.ai-json-details summary {{
  cursor: pointer;
  color: #52627a;
}}
.ai-json-details pre {{
  margin: 0;
  padding-left: 24px;
  border-left: 1px solid #d7dce5;
  color: #5f7880;
  font-size: 0.98rem;
  line-height: 1.7;
  white-space: pre-wrap;
}}
.ai-output-box {{
  min-height: 92px;
  max-height: 560px;
  overflow: auto;
  border-radius: 8px;
  background: #e8f2ff;
  color: #1966a8;
  padding: 20px;
  line-height: 1.55;
  white-space: pre-wrap;
}}
.ai-red-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: #ffffff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  width: fit-content;
}}
.ai-generation-status {{
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 28px;
  margin-top: 14px;
  color: #172033;
  font-size: 1rem;
}}
.ai-spinner {{
  width: 18px;
  height: 18px;
  border: 2px solid #d9dee7;
  border-top-color: #6b7280;
  border-radius: 999px;
  animation: ai-spin 0.85s linear infinite;
}}
@keyframes ai-spin {{
  to {{ transform: rotate(360deg); }}
}}
.insight-section {{
  display: grid;
  gap: 14px;
}}
.insight-input-row {{
  display: flex;
  gap: 12px;
  align-items: center;
  width: min(100%, 1040px);
  min-width: 0;
  margin-top: 10px;
}}
.insight-question-input {{
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
  margin: 0 !important;
}}
.insight-question-input div,
.insight-question-input .MuiFormControl-root,
.insight-question-input .MuiInputBase-root {{
  width: 100% !important;
  min-width: 0 !important;
}}
.insight-question-input label,
.insight-question-input .MuiInputLabel-root {{
  display: none !important;
}}
.insight-input-row input {{
  width: 100%;
  height: 48px;
  box-sizing: border-box;
  border: 1px solid #d8dee8;
  border-radius: 999px;
  background: #f1f3f7;
  color: #172033;
  padding: 0 22px;
  font-size: 1rem;
}}
.insight-send-btn {{
  flex: 0 0 96px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 48px;
  border: 0;
  border-radius: 999px;
  background: #2563eb;
  color: #ffffff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
}}
.insight-clear-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 46px;
  padding: 0 18px;
  border: 1px solid #d4d9e2;
  border-radius: 8px;
  background: #ffffff;
  color: #172033;
  font-size: 1rem;
  cursor: pointer;
  text-decoration: none;
}}
.insight-output {{
  min-height: 90px;
  color: #172033;
  line-height: 1.55;
  display: grid;
  gap: 14px;
  margin-top: 6px;
}}
@media (max-width: 1280px) {{
  .dashboard-shell {{ grid-template-columns:1fr; }}
  .sidebar-shell {{ min-height:auto; padding:24px; }}
  .main-shell {{ padding:40px 24px; }}
  .ai-analysis-section {{ grid-template-columns: 1fr; gap: 28px; }}
}}
@media (max-width: 640px) {{
  .insight-input-row {{
    flex-direction: column;
    width: 100%;
  }}
  .insight-send-btn {{
    width: 100%;
  }}
}}
</style>

<|layout|columns=306px 1|class_name=dashboard-shell|
<|part|class_name=sidebar-column|
{sidebar_html("ai-insights-chat")}
|>

<|part|class_name=main-shell|
<|part|class_name=ai-page|
<div class='page-header ai-header'>
    <div class='logo-shell'>
      <div class='logo-text'>AMPCUS</div>
      <div class='logo-subtext'>collaboration redefined</div>
    </div>
  </div>

  <h1 class='ai-title'>AI Analysis &amp; Chatbot</h1>
  <p class='ai-subtitle'>Use OpenAI to generate release insights and chat with the QA dashboard data.</p>

  <div class='ai-tabs'>
    <|AI Analysis|button|on_action=open_ai_analysis|class_name={{analysis_tab_class}}|>
    <|Insight Bot|button|on_action=open_insight_bot|class_name={{insight_tab_class}}|>
  </div>

<|part|render={{show_analysis}}|
<|layout|columns=1.08 0.92|class_name=ai-analysis-section|
<|part|class_name=ai-analysis-inputs|
## Analysis inputs

The AI analyzes the current dashboard snapshot, including KPIs, cycles, defects, trends, and root causes.

<details class='ai-json-details' open>
  <summary></summary>
  <pre>{snapshot_json}</pre>
</details>

<|Generate AI Analysis|button|on_action=generate_analysis|class_name=ai-red-btn|>

<|part|render={{analysis_loading}}|class_name=ai-generation-status|
<div class='ai-spinner'></div>
<|{{analysis_status_text}}|text|>
|>
|>

<|part|class_name=ai-latest-output|
## Latest output

<|{{analysis_output}}|text|mode=md|class_name=ai-output-box|>
|>
|>
|>

<|part|render={{show_insight}}|class_name=insight-section|
## Ask Insight Bot

Examples: Which cycle is riskiest? Why is pass rate low? What actions should the team take this week?

<|part|class_name=insight-input-row|
<|{{chat_question}}|input|on_action=ask_question|class_name=insight-question-input|>
<|Send|button|on_action=ask_question|class_name=insight-send-btn|>
|>

<|Clear chat history|button|on_action=clear_chat|class_name=insight-clear-btn|>

<|{{chat_history}}|text|mode=md|class_name=insight-output|>
|>
|>
|>
|>
"""

_tab_controls = """<|AI Analysis|button|on_action=open_ai_analysis|class_name={analysis_tab_class}|>
    <|Insight Bot|button|on_action=open_insight_bot|class_name={insight_tab_class}|>"""

_analysis_tabs = """<a class='ai-tab active' href='/ai-insights-chat'>AI Analysis</a>
    <a class='ai-tab' href='/ai-insights-chat-bot'>Insight Bot</a>"""

_bot_tabs = """<a class='ai-tab' href='/ai-insights-chat'>AI Analysis</a>
    <a class='ai-tab active' href='/ai-insights-chat-bot'>Insight Bot</a>"""

ai_chat = (
    page_body
    .replace(_tab_controls, _analysis_tabs)
    .replace("<|part|render={show_analysis}|", "<|part|render=True|")
    .replace("<|part|render={show_insight}|class_name=insight-section|", "<|part|render=False|class_name=insight-section|")
)

ai_chat_bot = (
    page_body
    .replace(_tab_controls, _bot_tabs)
    .replace("<|part|render={show_analysis}|", "<|part|render=False|")
    .replace("<|part|render={show_insight}|class_name=insight-section|", "<|part|render=True|class_name=insight-section|")
)
