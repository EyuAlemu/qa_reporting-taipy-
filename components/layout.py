import json
import html

from database.db import load_all_tables
from services.metrics_service import calculate_kpis
from services.openai_service import build_qa_context, qa_chatbot


sidebar_question = ""
sidebar_chat_history = ""


def ask_sidebar_question(state):
    question = str(state.sidebar_question or "").strip()
    if not question:
        return

    try:
        answer = qa_chatbot(question)
    except Exception as exc:
        answer = f"Error answering question: {exc}"

    state.sidebar_chat_history = (
        f"{state.sidebar_chat_history}\n\n"
        f"**You:** {question}\n\n"
        f"**Insight Bot:** {answer}"
    ).strip()
    state.sidebar_question = ""


def clear_sidebar_chat(state):
    state.sidebar_chat_history = ""
    state.sidebar_question = ""


def sidebar_metrics_json():
    try:
        return build_qa_context(load_all_tables(), row_limit=50)
    except Exception:
        try:
            kpis = calculate_kpis(load_all_tables())
        except Exception:
            kpis = {}

    return json.dumps({"kpis": kpis, "analytics": {}, "tables": {}})


def nav_link(icon_name, label, page, active_page):
    active_class = " nav-active" if page == active_page else ""
    text_color = "#000000"
    return (
        f"<a class='nav-link nav-form{active_class}' href='/{page}' "
        f"style='color:{text_color} !important; -webkit-text-fill-color:{text_color} !important; text-decoration:none !important;'>"
        f"<span class='nav-icon'><span class='nav-glyph nav-glyph-{icon_name}'></span></span>"
        f"<span class='nav-label' style='color:{text_color} !important; -webkit-text-fill-color:{text_color} !important;'>{label}</span>"
        f"</a>"
    )


def _sidebar_bot_srcdoc(metrics):
    metrics_json = json.dumps(metrics)
    doc = """
<!doctype html>
<html>
<head>
<style>
  html, body {
    margin: 0;
    padding: 0;
    background: transparent;
    color: #172033;
    font-family: Arial, sans-serif;
    overflow: hidden;
  }
  .bot-copy {
    margin: 0 0 12px 0;
    color: #020817;
    font-size: 14px;
    line-height: 1.35;
  }
  .chat-display {
    display: none;
    gap: 8px;
    max-height: 124px;
    overflow: auto;
    margin: 12px 0 0 0;
    font-size: 13px;
  }
  .chat-display.has-message {
    display: grid;
  }
  .chat-display::-webkit-scrollbar {
    width: 0;
    height: 0;
  }
  .chat-msg {
    padding: 10px 11px;
    border-radius: 8px;
    background: #ffffff;
    border: 1px solid #e1e5ec;
    overflow-wrap: anywhere;
    line-height: 1.38;
  }
  .chat-user { background: #eef2ff; border-color:#c7d2fe; }
  .chat-bot { background: #fff7ed; border-color:#fed7aa; }
  .chat-msg strong {
    display: block;
    margin-bottom: 4px;
    color: #172033;
  }
  .bot-input {
    width: 100%;
    box-sizing: border-box;
    height: 40px;
    border: 0;
    border-radius: 10px;
    background: #ffffff;
    margin: 0 0 14px 0;
    padding: 0 12px;
    color: #172033;
    font-size: 14px;
  }
  .bot-btn {
    width: 100%;
    height: 40px;
    border-radius: 9px;
    font-size: 14px;
    cursor: pointer;
    border: 0;
    background: #2563eb;
    color: #ffffff;
    font-weight: 700;
  }
  .bot-clear {
    margin-top: 12px;
    border: 1px solid #c7ccd6;
    background: #ffffff;
    color: #020817;
    border-radius: 9px;
    height: 40px;
  }
</style>
</head>
<body>
  <p class="bot-copy">Ask about cycles, defects, pass rate, root causes, risks...</p>
  <form id="form">
    <input id="question" class="bot-input" type="text" placeholder="Type your question..." />
    <button class="bot-btn" type="submit">Send</button>
  </form>
  <button id="clear" class="bot-btn bot-clear" type="button">Clear</button>
  <div id="display" class="chat-display"></div>
<script>
(function() {
  const context = __CONTEXT__;
  const metrics = context.kpis || {};
  const analytics = context.analytics || {};
  const tables = context.tables || {};

  function asNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function pct(value) {
    return asNumber(value).toFixed(1) + '%';
  }

  function rows(name) {
    return Array.isArray(analytics[name]) ? analytics[name] : [];
  }

  function tableRows(name) {
    return tables[name] && Array.isArray(tables[name].sample_rows) ? tables[name].sample_rows : [];
  }

  function norm(value) {
    return String(value || '').toLowerCase();
  }

  function title(value) {
    return String(value || '').trim();
  }

  function pickCycle(q) {
    const cycles = rows('test_execution_by_cycle').map(row => title(row.cycle_name)).filter(Boolean);
    return cycles.find(cycle => q.includes(cycle.toLowerCase()));
  }

  function topRows(items, valueKey, labelKey, limit) {
    return items
      .slice()
      .sort((a, b) => asNumber(b[valueKey]) - asNumber(a[valueKey]))
      .slice(0, limit)
      .map(row => title(row[labelKey]) + ': ' + asNumber(row[valueKey]))
      .join(', ');
  }

  function executionForCycle(cycle) {
    const row = rows('test_execution_by_cycle').find(item => norm(item.cycle_name) === norm(cycle));
    if (!row) return '';
    return cycle + ' has ' + asNumber(row.executed_test_cases) + ' executed of ' +
      asNumber(row.planned_test_cases) + ' planned test cases (' + pct(row.execution_pct) +
      ' execution), pass rate ' + pct(row.pass_rate_pct) + ', failed ' +
      asNumber(row.failed_test_cases) + ', blocked ' + asNumber(row.blocked_test_cases) +
      ', deferred ' + asNumber(row.deferred_test_cases) + '.';
  }

  function defectsForCycle(cycle) {
    const defectRows = rows('defects_per_cycle').filter(row => norm(row.cycle_name) === norm(cycle));
    if (!defectRows.length) return '';
    const total = defectRows.reduce((sum, row) => sum + asNumber(row.count), 0);
    const parts = defectRows
      .slice()
      .sort((a, b) => asNumber(b.count) - asNumber(a.count))
      .map(row => title(row.severity) + ': ' + asNumber(row.count))
      .join(', ');
    return cycle + ' has ' + total + ' defects by severity: ' + parts + '.';
  }

  function riskSummary() {
    const rootCause = rows('defects_by_root_cause').slice().sort((a, b) => asNumber(b.count) - asNumber(a.count))[0];
    const topCycle = rows('defects_by_cycle').slice().sort((a, b) => asNumber(b.count) - asNumber(a.count))[0];
    const lowestPass = rows('test_execution_by_cycle').slice().sort((a, b) => asNumber(a.pass_rate_pct) - asNumber(b.pass_rate_pct))[0];
    const focus = [];
    focus.push(asNumber(metrics.critical_defects) + ' critical defects');
    focus.push(asNumber(metrics.high_defects) + ' high defects');
    focus.push(asNumber(metrics.deferred_tests) + ' deferred tests');
    if (topCycle) focus.push('highest-defect cycle: ' + title(topCycle.cycle_name) + ' (' + asNumber(topCycle.count) + ')');
    if (lowestPass) focus.push('lowest pass cycle: ' + title(lowestPass.cycle_name) + ' (' + pct(lowestPass.pass_rate_pct) + ')');
    if (rootCause) focus.push('top root cause: ' + title(rootCause.root_cause) + ' (' + asNumber(rootCause.count) + ')');
    return focus.join('; ');
  }

  function answerQuestion(text) {
    const q = String(text || '').toLowerCase();
    const cycle = pickCycle(q);

    if (cycle && (q.includes('defect') || q.includes('bug') || q.includes('severity'))) {
      return defectsForCycle(cycle) || executionForCycle(cycle);
    }
    if (cycle) {
      return executionForCycle(cycle) || defectsForCycle(cycle) || 'I do not see detailed data for ' + cycle + ' in the current dashboard context.';
    }

    if (q.includes('cycle') && (q.includes('risk') || q.includes('riskiest') || q.includes('worst'))) {
      const defectCycles = rows('defects_by_cycle');
      const executionCycles = rows('test_execution_by_cycle');
      const topDefect = defectCycles.slice().sort((a, b) => asNumber(b.count) - asNumber(a.count))[0];
      const lowestPass = executionCycles.slice().sort((a, b) => asNumber(a.pass_rate_pct) - asNumber(b.pass_rate_pct))[0];
      const parts = [];
      if (topDefect) parts.push(title(topDefect.cycle_name) + ' has the most defects (' + asNumber(topDefect.count) + ')');
      if (lowestPass) parts.push(title(lowestPass.cycle_name) + ' has the lowest pass rate (' + pct(lowestPass.pass_rate_pct) + ')');
      return parts.length ? 'Risk signal by cycle: ' + parts.join('; ') + '.' : 'I do not see enough cycle-level data to rank risk.';
    }

    if (q.includes('root cause') || q.includes('cause')) {
      const rootCauses = rows('defects_by_root_cause').filter(row => asNumber(row.count) > 0);
      return rootCauses.length
        ? 'Defects by root cause: ' + topRows(rootCauses, 'count', 'root_cause', 6) + '.'
        : 'No root-cause defect counts are available in the current dashboard data.';
    }

    if (q.includes('status') || q.includes('open') || q.includes('closed') || q.includes('retest')) {
      const statusRows = rows('defect_status_distribution');
      return statusRows.length
        ? 'Defect status distribution: ' + topRows(statusRows, 'count', 'status', 5) + '.'
        : 'No defect status distribution is available in the current dashboard data.';
    }

    if (q.includes('severity') || q.includes('priority')) {
      const severityRows = rows('defects_by_severity');
      return severityRows.length
        ? 'Defects by severity: ' + topRows(severityRows, 'count', 'severity', 5) + '.'
        : 'Severity counts: Critical ' + asNumber(metrics.critical_defects) + ', High ' + asNumber(metrics.high_defects) + ', Medium ' + asNumber(metrics.medium_defects) + ', Low ' + asNumber(metrics.low_defects) + '.';
    }

    if (q.includes('trend') || q.includes('week')) {
      const weekly = rows('weekly_defect_trend');
      return weekly.length
        ? 'Weekly defect trend: ' + weekly.map(row => title(row.week) + ': ' + asNumber(row.count)).join(', ') + '.'
        : 'No weekly defect trend is available in the current dashboard data.';
    }

    if (q.includes('alert')) {
      const alerts = tableRows('alerts').filter(row => String(row.is_active || '').toUpperCase() === 'Y');
      return alerts.length
        ? 'Active alerts: ' + alerts.slice(0, 3).map(row => title(row.message)).join(' | ')
        : 'There are no active alerts in the loaded sample data.';
    }

    if (q.includes('test case') || q.includes('test cases') || q.includes('testcase') || q.includes('testcases')) {
      if (q.includes('executed') || q.includes('execution')) {
        return asNumber(metrics.executed_test_cases) + ' of ' + asNumber(metrics.total_test_cases) + ' test cases are executed, for an execution rate of ' + pct(metrics.execution_rate_pct) + '.';
      }
      if (q.includes('deferred')) {
        return 'There are ' + metrics.deferred_tests + ' deferred test cases.';
      }
      return 'There are a total of ' + asNumber(metrics.total_test_cases) + ' test cases; ' + asNumber(metrics.executed_test_cases) + ' are executed and ' + asNumber(metrics.deferred_tests) + ' are deferred.';
    }
    if (q.includes('total') && (q.includes('defect') || q.includes('bug'))) {
      return 'The total number of defects is ' + metrics.total_defects + '.';
    }
    if (q.includes('critical')) {
      return 'There are ' + metrics.critical_defects + ' critical defects.';
    }
    if (q.includes('high')) {
      return 'There are ' + metrics.high_defects + ' high severity defects.';
    }
    if (q.includes('pass')) {
      const lowestPass = rows('test_execution_by_cycle').slice().sort((a, b) => asNumber(a.pass_rate_pct) - asNumber(b.pass_rate_pct))[0];
      const failureNote = q.includes('why') || q.includes('low') || q.includes('issue') || q.includes('problem')
        ? ' Likely pressure points are failed/blocked/deferred tests and the severity mix: ' + riskSummary() + '.'
        : '';
      return 'The overall pass rate is ' + pct(metrics.pass_rate_pct) + (lowestPass ? '. Lowest cycle pass rate: ' + title(lowestPass.cycle_name) + ' at ' + pct(lowestPass.pass_rate_pct) + '.' : '.') + failureNote;
    }
    if (q.includes('execution') || q.includes('executed')) {
      return asNumber(metrics.executed_test_cases) + ' of ' + asNumber(metrics.total_test_cases) + ' test cases are executed, for an execution rate of ' + pct(metrics.execution_rate_pct) + '.';
    }
    if (q.includes('coverage') || q.includes('scope')) {
      return 'Scope coverage is ' + pct(metrics.scope_coverage_pct) + '.';
    }
    if (q.includes('deferred')) {
      return 'There are ' + metrics.deferred_tests + ' deferred tests.';
    }
    if (
      q.includes('risk') || q.includes('ready') || q.includes('release') ||
      q.includes('action') || q.includes('recommend') || q.includes('next step') ||
      q.includes('what should') || q.includes('what do') || q.includes('problem') ||
      q.includes('issue') || q.includes('blocker') || q.includes('concern')
    ) {
      return 'Release readiness focus: ' + riskSummary() + '. Recommended action: close critical/high defects first, unblock deferred tests, and target the leading cycle/root cause.';
    }
    return 'Dashboard snapshot: execution is ' + pct(metrics.execution_rate_pct) +
      ', pass rate is ' + pct(metrics.pass_rate_pct) +
      ', scope coverage is ' + pct(metrics.scope_coverage_pct) +
      ', and total defects are ' + asNumber(metrics.total_defects) +
      '. Main readiness signals: ' + riskSummary() + '.';
  }

  function addMessage(display, role, text) {
    const item = document.createElement('div');
    item.className = 'chat-msg chat-' + role;
    const label = document.createElement('strong');
    label.textContent = role === 'user' ? 'You: ' : 'Insight Bot: ';
    const body = document.createElement('span');
    body.textContent = text;
    item.appendChild(label);
    item.appendChild(body);
    display.appendChild(item);
    display.classList.add('has-message');
    display.scrollTop = display.scrollHeight;
  }

  window.ampcusSidebarBotSubmit = function(form) {
    const input = form.querySelector('.bot-input');
    const display = document.getElementById('display');
    if (!input || !display) return false;
    const text = input.value.trim();
    if (!text) return false;
    display.innerHTML = '';
    addMessage(display, 'user', text);
    addMessage(display, 'bot', answerQuestion(text));
    input.value = '';
    input.focus();
    return false;
  };

  window.ampcusSidebarBotClear = function() {
    const display = document.getElementById('display');
    if (display) {
      display.innerHTML = '';
      display.classList.remove('has-message');
    }
    const input = document.getElementById('question');
    if (input) input.value = '';
    if (input) input.focus();
    return false;
  };

  function bindSidebarBot() {
    const form = document.getElementById('form');
    const clear = document.getElementById('clear');
    if (!form || form.dataset.bound === '1') return;
    form.dataset.bound = '1';
    form.addEventListener('submit', function(event) {
      event.preventDefault();
      window.ampcusSidebarBotSubmit(form);
    });
    if (clear) {
      clear.addEventListener('click', function(event) {
        event.preventDefault();
        window.ampcusSidebarBotClear();
      });
    }
  }

  bindSidebarBot();
  let tries = 0;
  const timer = window.setInterval(function() {
    bindSidebarBot();
    tries += 1;
    const boundForm = document.getElementById('form');
    if (30 < tries || (boundForm && boundForm.dataset && boundForm.dataset.bound === '1')) {
      window.clearInterval(timer);
    }
  }, 250);
})();
</script>
"""
    doc = doc.replace("__CONTEXT__", metrics_json)
    return html.escape(doc, quote=True)


def sidebar_html(active_page):
    try:
        metrics = json.loads(sidebar_metrics_json())
    except Exception:
        metrics = {}
    srcdoc = _sidebar_bot_srcdoc(metrics)
    return f"""
<style>
.sidebar-shell .nav-link,
.sidebar-shell .nav-form,
.sidebar-shell .nav-link:link,
.sidebar-shell .nav-link:visited,
.sidebar-shell .nav-link:hover,
.sidebar-shell .nav-link:active,
.sidebar-shell .nav-link:focus,
.sidebar-shell .nav-link .nav-label,
.sidebar-shell .nav-link:link .nav-label,
.sidebar-shell .nav-link:visited .nav-label,
.sidebar-shell .nav-link:hover .nav-label,
.sidebar-shell .nav-link:active .nav-label,
.sidebar-shell .nav-link:focus .nav-label,
.sidebar-shell .nav-link *,
.sidebar-shell .nav-link:visited *,
.sidebar-shell .nav-link:hover *,
.sidebar-shell .nav-link:active *,
.sidebar-shell .nav-link:focus * {{
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  text-decoration: none !important;
  -webkit-text-decoration-line: none !important;
  text-decoration-line: none !important;
}}
.sidebar-shell .nav-link.nav-active,
.sidebar-shell .nav-form .nav-link.nav-active,
.sidebar-shell .nav-form .nav-link.nav-active *,
.sidebar-shell .nav-link.nav-active *,
.sidebar-shell .nav-link.nav-active:link,
.sidebar-shell .nav-link.nav-active:link *,
.sidebar-shell .nav-link.nav-active:visited,
.sidebar-shell .nav-link.nav-active:visited *,
.sidebar-shell .nav-link.nav-active:hover,
.sidebar-shell .nav-link.nav-active:hover *,
.sidebar-shell .nav-link.nav-active .nav-label,
.sidebar-shell .nav-link.nav-active:visited .nav-label,
.sidebar-shell .nav-link.nav-active:hover .nav-label {{
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  font-weight: 800 !important;
  text-decoration: none !important;
}}
.sidebar-shell .nav-icon {{
  width: 22px;
  height: 22px;
  display: inline-grid;
  place-items: center;
}}
.sidebar-shell .nav-glyph {{
  position: relative;
  width: 18px;
  height: 18px;
  display: inline-block;
  border-radius: 4px;
  background: #dbe7fb;
  box-shadow: inset 0 0 0 1px rgba(71, 85, 105, 0.16);
}}
.sidebar-shell .nav-glyph-chart::before {{
  content: "";
  position: absolute;
  left: 4px;
  bottom: 4px;
  width: 10px;
  height: 8px;
  border-left: 2px solid #2563eb;
  border-bottom: 2px solid #2563eb;
}}
.sidebar-shell .nav-glyph-chart::after {{
  content: "";
  position: absolute;
  left: 5px;
  top: 5px;
  width: 10px;
  height: 7px;
  border-top: 2px solid #7c3aed;
  border-right: 2px solid #7c3aed;
  transform: skew(-18deg);
}}
.sidebar-shell .nav-glyph-test {{
  background: linear-gradient(135deg, #dcfce7 0 45%, #bfdbfe 45% 100%);
}}
.sidebar-shell .nav-glyph-test::before {{
  content: "";
  position: absolute;
  left: 7px;
  top: 3px;
  width: 4px;
  height: 12px;
  border-radius: 3px;
  background: #22c55e;
  transform: rotate(45deg);
}}
.sidebar-shell .nav-glyph-defect {{
  border-radius: 50%;
  background: #fecdd3;
}}
.sidebar-shell .nav-glyph-defect::before {{
  content: "";
  position: absolute;
  left: 5px;
  top: 5px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e11d48;
}}
.sidebar-shell .nav-glyph-defect::after {{
  content: "";
  position: absolute;
  left: 3px;
  top: 8px;
  width: 12px;
  height: 2px;
  background: #831843;
}}
.sidebar-shell .nav-glyph-data {{
  background: #fbbf24;
  border-radius: 3px;
}}
.sidebar-shell .nav-glyph-data::before {{
  content: "";
  position: absolute;
  left: 2px;
  top: -2px;
  width: 8px;
  height: 5px;
  border-radius: 2px 2px 0 0;
  background: #fde68a;
}}
.sidebar-shell .nav-glyph-ai {{
  border-radius: 50%;
  background: #e0f2fe;
}}
.sidebar-shell .nav-glyph-ai::before {{
  content: "";
  position: absolute;
  left: 4px;
  top: 5px;
  width: 10px;
  height: 8px;
  border: 2px solid #0f172a;
  border-radius: 6px;
}}
.sidebar-shell .nav-glyph-ai::after {{
  content: "";
  position: absolute;
  left: 6px;
  top: 8px;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #0f172a;
  box-shadow: 5px 0 0 #0f172a;
}}
.sidebar-shell .sidebar-bot-frame {{
  width: 100%;
  height: 350px;
  border: none !important;
  display: block;
}}
.sidebar-shell {{
  position: fixed !important;
  top: 0;
  left: 0;
  bottom: 0;
  width: 306px;
  height: 100vh;
  box-sizing: border-box;
  z-index: 20;
  overflow-y: auto;
  overflow-x: hidden;
}}
.sidebar-shell::-webkit-scrollbar {{
  width: 8px;
}}
.sidebar-shell::-webkit-scrollbar-track {{
  background: transparent;
}}
.sidebar-shell::-webkit-scrollbar-thumb {{
  background: #cbd5e1;
  border-radius: 999px;
}}
.sidebar-shell {{
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}}
@media (max-width: 1280px) {{
  .sidebar-shell {{
    position: relative !important;
    width: auto;
    height: auto;
    min-height: auto;
  }}
}}
</style>
<div class='sidebar-shell'>
  <div class='nav-menu'>
    {nav_link('chart', 'Executive Overview', 'executive-overview', active_page)}
    {nav_link('test', 'Test Execution', 'test-execution', active_page)}
    {nav_link('defect', 'Defect Analytics', 'defect-analytics', active_page)}
    {nav_link('data', 'Data Management', 'data-management', active_page)}
    {nav_link('ai', 'AI Insights & Chat', 'ai-insights-chat', active_page)}
  </div>

  <div class='sidebar-rule compact'></div>
  <div class='sidebar-rule compact'></div>
  <div class='copyright'>&copy; Copyright Ampcus Inc. All Rights Reserved</div>
  <div class='sidebar-rule'></div>

  <div class='sidebar-footer'>
    <div class='bot-title'><span class='bot-title-icon nav-glyph nav-glyph-ai'></span> Insight Bot</div>
    <div class='bot-card'>
      <iframe class='sidebar-bot-frame' title='Insight Bot' srcdoc="{srcdoc}"></iframe>
    </div>
  </div>
</div>
<style>
.sidebar-shell .nav-menu a.nav-link,
.sidebar-shell .nav-menu a.nav-link:link,
.sidebar-shell .nav-menu a.nav-link:visited,
.sidebar-shell .nav-menu a.nav-link:hover,
.sidebar-shell .nav-menu a.nav-link:active,
.sidebar-shell .nav-menu a.nav-link:focus,
.sidebar-shell .nav-menu a.nav-link span,
.sidebar-shell .nav-menu a.nav-link:link span,
.sidebar-shell .nav-menu a.nav-link:visited span,
.sidebar-shell .nav-menu a.nav-link:hover span,
.sidebar-shell .nav-menu a.nav-link:active span,
.sidebar-shell .nav-menu a.nav-link:focus span,
.sidebar-shell .nav-menu .nav-label {{
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  text-decoration: none !important;
  -webkit-text-decoration-line: none !important;
  text-decoration-line: none !important;
}}
</style>
<script>
if (window.location.search === "?") {{
  window.history.replaceState(null, "", window.location.pathname + window.location.hash);
}}
</script>
"""

def build_page_shell(body, active_page):
    return f"""
<style>
html, body, #root {{ overflow-x:hidden !important; max-width:100%; scrollbar-width:none; -ms-overflow-style:none; }}
html::-webkit-scrollbar, body::-webkit-scrollbar, #root::-webkit-scrollbar {{ width:0; height:0; }}
.dashboard-shell {{ display:block; background:#ffffff; color:#111827; min-height:100vh; overflow-x:hidden; }}
.build-marker {{ position:fixed; right:8px; bottom:6px; z-index:9999; color:#94a3b8; font-size:11px; }}
.sidebar-shell {{ position:fixed; top:0; left:0; bottom:0; width:306px; height:100vh; box-sizing:border-box; z-index:20; display:flex; flex-direction:column; background:#f8fafc; padding:40px 28px 24px 16px; overflow-y:auto; overflow-x:hidden; scrollbar-width:thin; scrollbar-color:#cbd5e1 transparent; }}
.nav-menu {{ display:grid; gap:12px; }}
.nav-form {{ margin:0; padding:0; width:100%; }}
.nav-link {{ display:grid; grid-template-columns:24px minmax(0,1fr); align-items:center; column-gap:12px; width:100%; min-height:36px; padding:8px 16px; border:0; border-radius:8px; color:#000000; text-align:left; text-decoration:none; font-family:inherit; font-size:0.9rem; line-height:1.4; background:transparent; box-shadow:none; cursor:pointer; transition: all 0.2s ease; }}
.nav-link, .nav-form, .nav-link:link, .nav-link:visited, .nav-link:hover, .nav-link:active, .nav-link:focus, .nav-link .nav-label, .nav-link:link .nav-label, .nav-link:visited .nav-label, .nav-link:hover .nav-label, .nav-link * {{ color:#000000 !important; -webkit-text-fill-color:#000000 !important; text-decoration:none !important; }}
.nav-link.nav-active, .nav-form .nav-link.nav-active, .nav-form .nav-link.nav-active *, .nav-link.nav-active:link, .nav-link.nav-active:visited, .nav-link.nav-active:hover, .nav-link.nav-active .nav-label, .nav-link.nav-active:link .nav-label, .nav-link.nav-active:visited .nav-label, .nav-link.nav-active:hover .nav-label, .nav-link.nav-active *, .nav-link.nav-active:visited *, .nav-link.nav-active:hover * {{ color:#000000 !important; -webkit-text-fill-color:#000000 !important; text-decoration:none !important; font-weight:700 !important; }}
.nav-link:hover {{ background:#e2e8f0; }}
.nav-link.nav-active {{ background:#dbeafe; color:#000000; font-weight:700; }}
.nav-icon {{ display:inline-grid; place-items:center; width:22px; font-size:1.08rem; line-height:1; }}
.nav-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.sidebar-rule {{ height:1px; background:#c5cad3; margin:20px 0 20px 0; }}
.sidebar-rule.compact {{ margin:18px 0 18px 0; }}
.copyright {{ color:#8b919c; font-size:0.85rem; line-height:1.6; margin:4px 0 16px 0; }}
.sidebar-footer {{ margin-top:0; color:#172033; font-size:0.92rem; line-height:1.35; }}
.bot-title {{ display:flex; align-items:center; gap:6px; color:#172033; font-weight:700; font-size:1rem; margin-bottom:10px; }}
.bot-title-icon {{ font-size:0.9rem; }}
.bot-card {{ border:1px solid #c7ccd6; border-radius:8px; padding:14px; background:#f8f9fb; }}
.bot-copy {{ margin-bottom:8px; color:#172033; font-size:0.9rem; line-height:1.4; }}
.sidebar-bot-frame {{ width:100%; height:232px; border:0; display:block; }}
.sidebar-bot-form {{ margin:0; }}
.sidebar-chat-display {{ display:grid; gap:6px; max-height:120px; overflow:auto; margin:6px 0 8px 0; color:#172033; font-size:0.84rem; }}
.sidebar-chat-msg {{ padding:6px 8px; border-radius:6px; background:#ffffff; border:1px solid #e1e5ec; overflow-wrap:anywhere; }}
.sidebar-chat-user {{ background:#eef2ff; }}
.sidebar-chat-bot {{ background:#fff7ed; }}
.sidebar-bot-input {{ width:100%; height:38px; border:0; border-radius:8px; background:#ffffff; margin:6px 0 12px 0; padding:0 10px; color:#172033; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.8); font-size:0.9rem; }}
.sidebar-bot-btn {{ width:100%; height:40px; border-radius:8px; font-size:0.92rem; cursor:pointer; border:0; background:#2563eb; color:#ffffff; font-weight:600; display:flex; align-items:center; justify-content:center; text-decoration:none; }}
.sidebar-bot-btn:disabled {{ opacity:0.72; cursor:wait; }}
.sidebar-bot-clear-btn {{ margin-top:16px; border:1px solid #c7ccd6; background:#ffffff; color:#172033; }}
.main-shell {{ display:grid; gap:32px; align-content:start; margin-left:306px; padding:72px 34px 32px 58px; min-width:0; overflow-x:hidden; }}
.panel {{ background:#ffffff; border-radius:8px; padding:0; box-shadow:none; border:0; min-width:0; overflow:hidden; }}
.chart-grid {{ display:grid; grid-template-columns:1.6fr 1fr 1.2fr; gap:24px; }}
.overview-grid {{ display:grid; grid-template-columns:1.2fr 1.2fr 0.8fr 0.8fr; gap:24px; align-items:start; }}
.metric-card-panel {{ padding:24px; border-radius:24px; background:#f8fafc; border:1px solid rgba(148,163,184,0.18); }}
.metric-label {{ color:#475569; font-size:0.95rem; text-transform:uppercase; letter-spacing:0.12em; margin-bottom:12px; }}
.metric-value {{ font-size:3rem; font-weight:800; color:#0f172a; line-height:1; margin-bottom:8px; }}
.metric-note {{ color:#64748b; font-size:0.95rem; }}
.section-heading {{ font-size:1.2rem; font-weight:700; margin-bottom:16px; }}
.stats-list {{ display:grid; gap:12px; margin-top:12px; }}
.stats-item {{ display:flex; justify-content:space-between; align-items:center; padding:14px 18px; border-radius:18px; background:#f8fafc; }}
.stats-item strong {{ font-size:1rem; color:#0f172a; }}
.stats-item span {{ color:#475569; }}
.page-header {{ display:grid; gap:10px; justify-items:center; text-align:center; }}
.logo-shell {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
.logo-text {{ font-size:3.35rem; font-weight:500; letter-spacing:-0.06em; color:#1681bd; font-family:Georgia, 'Times New Roman', serif; }}
.logo-subtext {{ font-size:1.4rem; color:#4b5563; letter-spacing:0; }}
.page-title {{ font-size:2.4rem; font-weight:800; margin:0; color:#0f172a; }}
.page-date {{ color:#64748b; font-size:0.95rem; }}
.execution-chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:48px; align-items:start; }}
.execution-table {{ overflow:auto; overflow-y:hidden; border:1px solid #e5e7eb; border-radius:9px; }}
.data-table {{ width:100%; border-collapse:collapse; font-size:0.95rem; }}
.data-table th {{ background:#f8fafc; color:#6b7280; font-weight:500; text-align:left; border-bottom:1px solid #e5e7eb; padding:12px 10px; white-space:nowrap; }}
.data-table td {{ color:#111827; border-bottom:1px solid #e5e7eb; padding:12px 10px; white-space:nowrap; }}
.data-select {{ min-width:260px; height:42px; border:1px solid #cbd5e1; border-radius:8px; padding:0 12px; background:#ffffff; color:#111827; font-size:1rem; }}
.empty-chart {{ min-height:180px; display:grid; place-items:center; color:#64748b; background:#f8fafc; border-radius:8px; }}
.css-chart {{ min-height:390px; }}
.css-chart h3 {{ margin:0 0 22px 0; color:#111827; font-size:1.1rem; }}
.css-chart-body {{ display:grid; grid-template-columns:34px minmax(0,1fr); min-height:285px; align-items:end; }}
.css-y-axis {{ writing-mode:vertical-rl; transform:rotate(180deg); color:#68738a; align-self:center; justify-self:center; font-size:0.95rem; }}
.css-bars {{ height:285px; display:grid; grid-template-columns:repeat(4, minmax(70px,1fr)); gap:28px; align-items:end; border-bottom:1px solid #e5e7eb; background:repeating-linear-gradient(to top, transparent 0, transparent 59px, #dfe5ef 60px); padding:0 14px; }}
.css-bar-item {{ height:100%; display:grid; grid-template-rows:1fr auto; gap:10px; min-width:0; }}
.css-bar-track {{ height:100%; display:flex; align-items:end; justify-content:center; }}
.css-bar {{ width:100%; max-width:116px; display:flex; align-items:flex-start; justify-content:center; padding-top:10px; font-weight:700; font-size:0.9rem; }}
.css-bar-label {{ text-align:center; color:#68738a; font-size:0.85rem; }}
.css-x-axis {{ color:#68738a; text-align:center; margin-top:8px; font-size:0.95rem; }}
.progress-panel {{ display:grid; gap:14px; min-height:180px; align-content:center; }}
.progress-value {{ color:#0f172a; font-size:2.2rem; font-weight:800; }}
.progress-track {{ height:14px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
.progress-fill {{ height:100%; border-radius:999px; }}
.mini-bars {{ display:grid; gap:14px; }}
.mini-bar-row {{ display:grid; grid-template-columns:minmax(110px, 1fr) 2fr 42px; gap:12px; align-items:center; color:#475569; }}
.mini-bar-row span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.mini-bar-row strong {{ color:#0f172a; text-align:right; }}
.mini-bar-track {{ height:12px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
.mini-bar-fill {{ height:100%; background:#0b6fc6; border-radius:999px; }}
.defect-page-title {{ font-size:2.6rem; font-weight:800; color:#172033; margin:0 0 18px 8px; }}
.defect-header {{ margin-top:-28px; margin-bottom:20px; }}
.defect-header .logo-text {{ font-size:3.85rem; }}
.defect-header .logo-subtext {{ font-size:1.35rem; }}
.defect-grid {{ display:grid; grid-template-columns:1fr 1fr; column-gap:72px; row-gap:54px; align-items:start; }}
.defect-chart {{ min-height:315px; color:#111827; }}
.defect-chart h3 {{ margin:0 0 28px 0; text-align:center; font-size:1.18rem; font-weight:800; }}
.defect-chart-layout {{ display:grid; grid-template-columns:42px 28px minmax(0,1fr) 112px; gap:16px; min-height:260px; align-items:end; }}
.defect-y-axis, .line-y-axis {{ writing-mode:vertical-rl; transform:rotate(180deg); align-self:center; justify-self:center; color:#68738a; font-size:0.95rem; }}
.defect-y-ticks {{ height:230px; display:grid; align-content:space-between; align-self:start; color:#68738a; font-size:0.86rem; padding-top:0; text-align:right; }}
.defect-vplot {{ height:260px; display:grid; grid-template-columns:repeat(4, minmax(86px,1fr)); gap:28px; align-items:stretch; padding:0 12px; }}
.defect-vgroup {{ height:100%; display:grid; grid-template-rows:230px 26px; gap:10px; min-width:0; }}
.defect-vbars {{ display:flex; align-items:end; justify-content:center; gap:0; height:230px; border-bottom:1px solid #dfe5ef; background:repeating-linear-gradient(to top, transparent 0, transparent 76px, #dfe5ef 77px); }}
.defect-vbar {{ width:24px; min-height:0; }}
.defect-axis-label {{ text-align:center; color:#68738a; font-size:0.9rem; }}
.defect-x-axis {{ margin-top:10px; text-align:center; color:#68738a; font-size:0.95rem; }}
.defect-legend {{ align-self:start; display:grid; gap:8px; color:#111827; font-size:0.9rem; }}
.defect-legend div {{ display:flex; align-items:center; gap:10px; }}
.defect-legend span {{ display:inline-block; width:14px; height:14px; }}
.line-chart-wrap {{ display:grid; grid-template-columns:42px 34px minmax(0,1fr); min-height:230px; align-items:stretch; }}
.line-y-labels {{ display:grid; align-content:space-between; color:#68738a; font-size:0.86rem; padding:0 0 0 0; }}
.line-chart {{ position:relative; width:100%; height:230px; aspect-ratio:2.17/1; overflow:hidden; background:repeating-linear-gradient(to top, transparent 0, transparent 43px, #dfe5ef 44px); }}
.line-chart-img {{ display:block; width:100%; height:100%; }}
.line-x-labels {{ display:grid; grid-template-columns:repeat(5,1fr); color:#68738a; font-size:0.85rem; margin-left:76px; margin-top:10px; }}
.line-x-labels span {{ text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.severity-cycle-chart .defect-chart-layout {{ grid-template-columns:42px 34px minmax(0,1fr) 112px; gap:14px; }}
.severity-cycle-chart .defect-vplot {{ grid-template-columns:repeat(4, minmax(58px,1fr)); gap:18px; padding:0 6px; }}
.severity-cycle-chart .defect-vbar {{ width:18px; }}
.severity-cycle-chart .severity-legend {{ align-self:start; display:grid; gap:10px; margin:0; padding:2px 0 0 4px; font-size:0.9rem; background:#ffffff; }}
.severity-cycle-chart .severity-legend div {{ white-space:nowrap; }}
.status-chart {{ display:grid; grid-template-columns:minmax(0,1fr) 128px; gap:28px; align-items:center; min-height:250px; }}
.status-rows {{ display:grid; gap:34px; }}
.status-row {{ display:grid; grid-template-columns:150px minmax(0,1fr); gap:14px; align-items:center; }}
.status-label {{ color:#52627a; text-align:right; }}
.status-track {{ height:48px; display:flex; align-items:stretch; border-left:1px solid #cbd5e1; }}
.status-segment {{ display:flex; align-items:center; justify-content:center; color:#ffffff; min-width:30px; }}
.root-chart {{ display:grid; gap:8px; margin-top:6px; }}
.root-row {{ display:grid; grid-template-columns:minmax(190px,1fr) minmax(0,1.4fr); gap:12px; align-items:center; }}
.root-label {{ color:#68738a; font-size:0.84rem; text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.root-track {{ position:relative; height:24px; background:#e5e7eb; }}
.root-fill {{ height:100%; min-width:24px; background:#0b6fc6; color:#ffffff; display:flex; align-items:center; justify-content:flex-end; padding-right:8px; font-weight:800; font-size:0.82rem; }}
.root-fill.root-zero {{ min-width:0; padding-right:0; }}
.root-zero-count {{ position:absolute; left:8px; top:50%; transform:translateY(-50%); color:#68738a; font-weight:800; font-size:0.82rem; }}
.defect-table {{ margin-top:16px; }}
.overview-header {{ margin-top:-28px; }}
.overview-title {{ color:#172033; font-size:2.55rem; font-weight:800; margin:34px 0 24px 8px; }}
.overview-date {{ color:#7a8495; font-size:1rem; margin:0 0 28px 8px; }}
.overview-top-grid {{ display:grid; grid-template-columns:1fr 1fr 1.1fr 0.8fr; gap:56px; align-items:start; margin:0 0 58px 8px; }}
.overview-metric, .overview-defects, .overview-summary {{ min-height:170px; }}
.overview-label {{ color:#0f172a; font-size:1rem; margin-bottom:16px; }}
.overview-big {{ color:#172033; font-size:2.45rem; line-height:1; margin-bottom:34px; }}
.overview-big.small {{ font-size:2.25rem; margin-bottom:38px; }}
.overview-note {{ color:#68738a; font-size:1rem; }}
.overview-defects h3 {{ margin:0 0 26px 0; font-size:1.12rem; }}
.overview-severity {{ font-weight:800; font-size:1.02rem; margin-bottom:28px; }}
.overview-summary {{ display:grid; gap:34px; }}
.overview-chart-row {{ display:grid; grid-template-columns:minmax(0,0.92fr) minmax(0,0.92fr) minmax(0,1.08fr); gap:28px; align-items:start; margin-bottom:48px; overflow:hidden; }}
.overview-bottom-row {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,0.95fr) minmax(0,1fr); gap:32px; align-items:start; overflow:hidden; }}
.overview-chart-title {{ text-align:center; font-size:1.22rem; margin:0 0 38px 0; }}
.overview-gauge {{ min-height:260px; display:flex; align-items:center; justify-content:center; overflow:visible; }}
.gauge-arc {{ position:relative; width:310px; height:155px; border-radius:310px 310px 0 0; background:conic-gradient(from 270deg, #6b8ff4 0 9%, #fff0f0 9% 50%, #fff6df 50% 78%, #efffe6 78% 100%); border:1px solid #333; border-bottom:0; }}
.gauge-arc::after {{ content:''; position:absolute; left:38px; right:38px; bottom:0; height:116px; border-radius:230px 230px 0 0; background:#ffffff; border:1px solid #333; border-bottom:0; }}
.gauge-needle {{ position:absolute; left:50%; bottom:0; width:3px; height:120px; background:#475569; transform-origin:bottom center; z-index:2; }}
.gauge-center {{ position:absolute; left:0; right:0; bottom:18px; z-index:3; text-align:center; color:#858999; font-size:3.7rem; }}
.gauge-min, .gauge-mid, .gauge-max {{ position:absolute; color:#64748b; font-size:0.9rem; }}
.gauge-min {{ left:-18px; bottom:-6px; }}
.gauge-mid {{ top:-24px; left:50%; transform:translateX(-50%); }}
.gauge-max {{ right:-24px; bottom:-6px; }}
.scope-wrap {{ display:flex; align-items:center; justify-content:center; gap:34px; min-height:260px; }}
.scope-donut {{ position:relative; width:220px; height:220px; border-radius:999px; display:grid; place-items:center; }}
.scope-hole {{ width:120px; height:120px; border-radius:999px; background:#ffffff; display:grid; place-items:center; align-content:center; gap:8px; color:#111827; }}
.scope-hole strong {{ font-size:2rem; line-height:1; }}
.scope-hole span {{ color:#68738a; font-size:0.9rem; }}
.scope-slice-label {{ position:absolute; z-index:3; display:inline-flex; align-items:center; justify-content:center; min-width:46px; height:24px; padding:0 8px; border-radius:999px; color:#ffffff; font-size:0.88rem; font-weight:800; line-height:1; box-shadow:0 2px 8px rgba(15,23,42,0.28); pointer-events:none; }}
.scope-executed-label {{ left:42px; bottom:56px; background:#1378ca; }}
.scope-pending-label {{ left:56px; top:38px; background:#fb9a66; }}
.scope-legend {{ display:grid; gap:12px; color:#111827; }}
.scope-legend div {{ display:flex; align-items:center; gap:12px; }}
.scope-legend span {{ width:14px; height:14px; display:inline-block; }}
.overview-small-chart {{ min-height:285px; }}
.overview-small-chart h3 {{ margin-bottom:22px; }}
.overview-small-chart .defect-chart-layout {{ min-height:235px; grid-template-columns:30px 22px minmax(0,1fr) 78px; gap:8px; }}
.overview-small-chart .defect-y-ticks {{ height:205px; }}
.overview-small-chart .defect-vplot {{ height:235px; grid-template-columns:repeat(4, minmax(48px,1fr)); gap:12px; padding:0 4px; }}
.overview-small-chart .defect-vgroup {{ grid-template-rows:205px 24px; }}
.overview-small-chart .defect-vbars {{ height:205px; }}
.overview-small-chart .defect-vbar {{ width:18px; }}
.overview-small-chart .defect-axis-label {{ font-size:0.82rem; }}
.overview-small-chart .defect-legend {{ font-size:0.78rem; gap:7px; }}
.overview-small-chart .defect-legend div {{ gap:8px; }}
.overview-small-chart .defect-legend span {{ width:13px; height:13px; }}
.overview-small-chart .status-chart {{ grid-template-columns:minmax(0,1fr) 82px; gap:14px; min-height:240px; align-items:center; }}
.overview-small-chart .status-rows {{ gap:30px; min-width:0; }}
.overview-small-chart .status-row {{ grid-template-columns:112px minmax(0,1fr); gap:10px; }}
.overview-small-chart .status-label {{ font-size:0.88rem; white-space:normal; line-height:1.2; }}
.overview-small-chart .status-track {{ height:44px; min-width:0; }}
.overview-small-chart .status-segment {{ min-width:24px; font-size:0.86rem; }}
.overview-small-chart .root-row {{ grid-template-columns:minmax(116px,0.95fr) minmax(0,1fr); }}
.overview-small-chart .root-label {{ font-size:0.82rem; }}
.alerts-list {{ max-width:100%; overflow:hidden; }}
.alerts-title {{ margin:0 0 22px 0; font-size:2rem; color:#172033; }}
.alerts-list {{ display:grid; gap:20px; }}
.alert-card {{ border-radius:8px; padding:22px 20px; font-size:1.15rem; line-height:1.55; }}
.alert-card {{ overflow:hidden; overflow-wrap:anywhere; }}
.alert-high {{ background:#fde5e5; color:#d82727; }}
.alert-medium {{ background:#fffce3; color:#a66b00; }}
@media (max-width: 1280px) {{ .dashboard-shell {{ display:block; }} .sidebar-shell {{ position:relative; width:auto; height:auto; min-height:auto; padding:24px; }} .main-shell {{ margin-left:0; padding:40px 24px; }} .overview-grid, .chart-grid, .execution-chart-grid, .defect-grid, .overview-top-grid, .overview-chart-row, .overview-bottom-row {{ grid-template-columns:1fr; }} }}
</style>
<div class='dashboard-shell'>
  <div class='build-marker'>Updated build 2026-04-24 18:15</div>
  {sidebar_html(active_page)}
  <div class='main-shell'>
    {body}
  </div>
</div>
"""
