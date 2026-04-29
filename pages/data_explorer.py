import sqlite3

import pandas as pd
from taipy.gui import notify

from components.layout import sidebar_html
from database.db import get_db_connection, read_table


cycle_name = ""
planned = 0
executed = 0
passed = 0
failed = 0
blocked = 0
deferred = 0
scope_executed = 80.0
scope_pending = 20.0

defect_id = ""
cycle_selected = ""
scenario_id = ""
testcase_id = ""
severity = "Critical"
status = "Open"
root_cause = "Code"
week = "Week 1"
show_cycle_form = False
show_defect_form = False
cycle_expander_label = "+ Add test cycle"
defect_expander_label = "+ Add defect"

test_execution_data = pd.DataFrame()
defect_data = pd.DataFrame()
cycle_options = []
severity_options = ["Critical", "High", "Medium", "Low"]
status_options = ["Open", "Fixed, in Retest", "Closed/Deferred"]
root_cause_options = ["Code", "Stored Proc", "UI", "Environment", "Configuration", "Database"]


def _sync_expander_labels(state=None):
    global cycle_expander_label, defect_expander_label

    cycle_expander_label = "- Add test cycle" if show_cycle_form else "+ Add test cycle"
    defect_expander_label = "- Add defect" if show_defect_form else "+ Add defect"

    if state is not None:
        state.cycle_expander_label = cycle_expander_label
        state.defect_expander_label = defect_expander_label


def toggle_cycle_form(state):
    global show_cycle_form

    show_cycle_form = not bool(state.show_cycle_form)
    state.show_cycle_form = show_cycle_form
    _sync_expander_labels(state)


def toggle_defect_form(state):
    global show_defect_form

    show_defect_form = not bool(state.show_defect_form)
    state.show_defect_form = show_defect_form
    _sync_expander_labels(state)


def _to_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_pct(value):
    try:
        pct = max(0, min(float(value or 0), 100))
    except (TypeError, ValueError):
        pct = 0
    return f"{pct:.0f}%"


def _to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def refresh_data(state=None):
    global test_execution_data, defect_data, cycle_options, cycle_selected

    test_execution_data = read_table("test_execution")
    defect_data = read_table("defects")
    cycle_options = (
        test_execution_data["environment"].dropna().astype(str).tolist()
        if not test_execution_data.empty and "environment" in test_execution_data.columns
        else []
    )
    cycle_selected = cycle_options[0] if cycle_options else ""

    if state is not None:
        state.test_execution_data = test_execution_data
        state.defect_data = defect_data
        state.cycle_options = cycle_options
        state.cycle_selected = cycle_selected


def add_cycle(state):
    name = str(state.cycle_name or "").strip()
    if not name:
        notify(state, "warning", "Cycle name is required.")
        return

    planned_count = _to_int(state.planned)
    executed_count = _to_int(state.executed)
    passed_count = _to_int(state.passed)
    failed_count = _to_int(state.failed)
    blocked_count = _to_int(state.blocked)
    deferred_count = _to_int(state.deferred)
    scope_executed_value = _to_float(state.scope_executed)
    scope_pending_value = _to_float(state.scope_pending)

    counts = {
        "Executed": executed_count,
        "Passed": passed_count,
        "Failed": failed_count,
        "Blocked": blocked_count,
        "Deferred": deferred_count,
    }

    if planned_count <= 0:
        notify(state, "warning", "Planned test cases must be greater than 0.")
        return
    negative_fields = [label for label, value in counts.items() if value < 0]
    if negative_fields:
        notify(state, "warning", f"{', '.join(negative_fields)} test cases cannot be negative.")
        return
    if not 0 <= scope_executed_value <= 100 or not 0 <= scope_pending_value <= 100:
        notify(state, "warning", "Scope percentages must be between 0 and 100.")
        return
    if abs((scope_executed_value + scope_pending_value) - 100) > 0.1:
        notify(state, "warning", "Scope executed and pending percentages must total 100.")
        return
    if executed_count > planned_count:
        notify(state, "warning", "Executed test cases cannot be greater than planned test cases.")
        return
    if passed_count + failed_count + blocked_count > executed_count:
        notify(state, "warning", "Passed, failed, and blocked counts cannot exceed executed test cases.")
        return
    if deferred_count > planned_count - executed_count:
        notify(state, "warning", "Deferred test cases cannot exceed not-executed test cases.")
        return

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO test_execution (
                environment, source_filename, planned_test_cases,
                total_executed_test_cases, total_not_executed,
                total_passed_test_cases, total_failed_test_cases,
                blocked_test_cases, deferred_test_cases,
                scope_executed_pct, scope_pending_pct,
                outof_scope_testcases, active_flag, created_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
            """,
            (
                name,
                f"{name}_results.xlsx",
                planned_count,
                executed_count,
                max(planned_count - executed_count, 0),
                passed_count,
                failed_count,
                blocked_count,
                deferred_count,
                _to_pct(scope_executed_value),
                _to_pct(scope_pending_value),
                0,
            ),
        )
        conn.commit()
        notify(state, "success", "Test cycle added.")
        refresh_data(state)
    finally:
        conn.close()


def add_defect(state):
    new_defect_id = str(state.defect_id or "").strip()
    if not new_defect_id:
        notify(state, "warning", "Defect ID is required.")
        return
    if not str(state.cycle_selected or "").strip():
        notify(state, "warning", "Cycle is required before adding a defect.")
        return

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO defects (
                defect_id,
                cycle_name,
                scenario_id,
                testcase_id,
                severity,
                status,
                root_cause,
                discovered_week
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_defect_id,
                state.cycle_selected,
                state.scenario_id,
                state.testcase_id,
                state.severity,
                state.status,
                state.root_cause,
                state.week,
            ),
        )
        conn.commit()
        notify(state, "success", "Defect added.")
        refresh_data(state)
    except sqlite3.IntegrityError:
        notify(state, "warning", "Defect ID already exists.")
    finally:
        conn.close()


try:
    refresh_data()
except Exception:
    test_execution_data = pd.DataFrame()
    defect_data = pd.DataFrame()
    cycle_options = []
    cycle_selected = ""


data_explorer = """
<style>
.dashboard-shell { display:grid; grid-template-columns:306px minmax(0,1fr); background:#ffffff; color:#111827; min-height:100vh; }
.sidebar-shell { display:flex; flex-direction:column; background:#f0f2f6; padding:54px 25px 18px 12px; min-height:100vh; }
.nav-menu { display:grid; gap:8px; }
.nav-form { margin:0; padding:0; width:100%; }
.nav-link { display:grid; grid-template-columns:22px minmax(0,1fr); align-items:center; column-gap:9px; width:100%; min-height:34px; padding:6px 12px; border:0; border-radius:9px; color:#000000; text-align:left; text-decoration:none; font-family:inherit; font-size:0.98rem; line-height:1.32; background:transparent; box-shadow:none; cursor:pointer; }
.nav-link, .nav-form, .nav-link:visited, .nav-link:hover, .nav-link:active, .nav-link:focus, .nav-link .nav-label, .nav-link:visited .nav-label, .nav-link:hover .nav-label, .nav-link * { color:#000000 !important; -webkit-text-fill-color:#000000 !important; text-decoration:none !important; }
.nav-link.nav-active, .nav-form .nav-link.nav-active, .nav-form .nav-link.nav-active *, .nav-link.nav-active:visited, .nav-link.nav-active:hover, .nav-link.nav-active .nav-label, .nav-link.nav-active:visited .nav-label, .nav-link.nav-active:hover .nav-label, .nav-link.nav-active *, .nav-link.nav-active:visited *, .nav-link.nav-active:hover * { color:#000000 !important; -webkit-text-fill-color:#000000 !important; text-decoration:none !important; font-weight:800 !important; }
.nav-link:hover { background:#e4e8f0; box-shadow:none; }
.nav-link.nav-active { background:#dbeafe; color:#000000; font-weight:800; }
.nav-icon { display:inline-grid; place-items:center; width:22px; font-size:1.08rem; line-height:1; }
.nav-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.sidebar-rule { height:1px; background:#c5cad3; margin:20px 0 20px 0; }
.sidebar-rule.compact { margin:18px 0 18px 0; }
.copyright { color:#8b919c; font-size:0.98rem; line-height:1.7; margin:4px 0 18px 0; }
.sidebar-footer { margin-top:0; color:#172033; font-size:0.98rem; line-height:1.5; }
.bot-title { display:flex; align-items:center; gap:6px; color:#172033; font-weight:800; font-size:1.16rem; margin-bottom:14px; }
.bot-title-icon { font-size:0.95rem; }
.bot-card { border:1px solid #c7ccd6; border-radius:9px; padding:18px 18px 16px 18px; background:#f8f9fb; }
.main-shell { display:grid; gap:24px; align-content:start; padding:86px 66px 26px 100px; min-width:0; }
.page-header { display:grid; gap:10px; justify-items:center; text-align:center; }
.logo-shell { display:flex; flex-direction:column; align-items:center; gap:4px; }
.logo-text { font-size:3.35rem; font-weight:500; letter-spacing:-0.06em; color:#1681bd; font-family:Georgia, 'Times New Roman', serif; }
.logo-subtext { font-size:1.4rem; color:#4b5563; letter-spacing:0; }
.execution-table { overflow:auto; border:1px solid #e5e7eb; border-radius:9px; }
.data-table { width:100%; border-collapse:collapse; font-size:0.95rem; }
.data-table th { background:#f8fafc; color:#6b7280; font-weight:500; text-align:left; border-bottom:1px solid #e5e7eb; padding:12px 10px; white-space:nowrap; }
.data-table td { color:#111827; border-bottom:1px solid #e5e7eb; padding:12px 10px; white-space:nowrap; }
.data-management-page { display:grid; gap:20px; max-width:1380px; }
.data-header { margin:0 0 28px 0; }
.data-header .logo-text { font-size:3.9rem; }
.data-header .logo-subtext { font-size:1.3rem; }
.data-page-title { margin:0 0 4px 0; color:#172033; font-size:2.45rem; font-weight:800; }
.data-accordion-stack { display:grid; gap:20px; margin-bottom:18px; max-width:1380px; }
.data-accordion { border:1px solid #d4d9e2; border-radius:8px; background:#ffffff; overflow:visible; padding:0 0 22px 0; }
.data-accordion-title { min-height:48px; display:flex; align-items:center; gap:14px; padding:0 22px; color:#172033; font-size:1.08rem; }
.data-expander-btn { width:100%; min-height:48px; display:flex; align-items:center; justify-content:flex-start; padding:0 22px; border:0; background:transparent; color:#172033; font-size:1.08rem; font-weight:500; text-align:left; box-shadow:none; cursor:pointer; }
.data-expander-btn:hover { background:#f8fafc; box-shadow:none; }
.data-chevron { color:#172033; font-size:1.1rem; line-height:1; }
.data-field-grid { display:grid; grid-template-columns:1fr 1fr; column-gap:24px; row-gap:18px; padding:10px 22px 22px 22px; max-width:900px; }
.data-field { display:grid; gap:7px; align-content:start; min-width:0; }
.data-field-label { color:#34405a; font-size:0.95rem; font-weight:700; line-height:1.2; }
.data-field-grid .MuiFormControl-root,
.data-field-grid .MuiTextField-root,
.data-field-grid .MuiInputBase-root,
.data-field-grid .MuiAutocomplete-root,
.data-field-grid .taipy-input,
.data-field-grid .taipy-number,
.data-field-grid .taipy-selector {
  width:100% !important;
  min-width:0 !important;
}
.data-field-grid label,
.data-field-grid .MuiFormLabel-root,
.data-field-grid .MuiInputLabel-root {
  display:none !important;
}
.data-field-grid input,
.data-field-grid select,
.data-field-grid textarea,
.data-field-grid .MuiInputBase-input {
  min-height:44px !important;
  color:#172033 !important;
  font-size:1rem !important;
  background:#ffffff !important;
}
.data-field-grid .MuiInputBase-root,
.data-field-grid .MuiOutlinedInput-root {
  min-height:50px !important;
  border-radius:8px !important;
  background:#ffffff !important;
}
.data-field-grid .MuiOutlinedInput-notchedOutline {
  border-color:#b8c0cc !important;
  border-width:1.4px !important;
}
.data-field-grid .MuiInputBase-root:hover .MuiOutlinedInput-notchedOutline,
.data-field-grid .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline {
  border-color:#6b7a90 !important;
}
.data-field-grid .Mui-focused .MuiOutlinedInput-notchedOutline {
  border-color:#2563eb !important;
  border-width:2px !important;
}
.data-section-title { margin:0 0 2px 0; color:#172033; font-size:2rem; font-weight:800; }
.data-table-card h2,
.data-table-heading { margin:16px 0 20px 0; color:#172033; font-size:1.65rem; font-weight:800; }
.data-primary-btn { margin:2px 0 0 22px; height:44px; padding:0 22px; border:0; border-radius:8px; background:#2563eb; color:#ffffff; font-size:1rem; font-weight:700; cursor:pointer; }
.data-table-card { overflow:hidden; }
.data-table-card .execution-table {
  overflow:auto;
  border:1px solid #e5e7eb !important;
  border-radius:9px;
  background:#ffffff !important;
  box-shadow:none !important;
}
.data-table-card table,
.data-table-card .MuiTable-root {
  width:100%;
  border-collapse:collapse !important;
  background:#ffffff !important;
  font-size:0.95rem !important;
}
.data-table-card th,
.data-table-card .MuiTableHead-root .MuiTableCell-root,
.data-table-card .MuiDataGrid-columnHeaders,
.data-table-card .MuiDataGrid-columnHeader {
  background:#f8fafc !important;
  color:#6b7280 !important;
  font-weight:500 !important;
  text-align:left !important;
  border-color:#e5e7eb !important;
  border-bottom:1px solid #e5e7eb !important;
}
.data-table-card td,
.data-table-card .MuiTableBody-root .MuiTableCell-root,
.data-table-card .MuiDataGrid-cell {
  color:#111827 !important;
  background:#ffffff !important;
  border-color:#e5e7eb !important;
  border-bottom:1px solid #e5e7eb !important;
}
.data-table-card th,
.data-table-card td,
.data-table-card .MuiTableCell-root,
.data-table-card .MuiDataGrid-cell,
.data-table-card .MuiDataGrid-columnHeader {
  padding:12px 10px !important;
  white-space:nowrap !important;
  font-size:0.95rem !important;
}
.data-table-card .MuiDataGrid-root,
.data-table-card .MuiPaper-root {
  border:0 !important;
  background:#ffffff !important;
  color:#111827 !important;
  box-shadow:none !important;
}
.data-table-card .MuiDataGrid-row:hover,
.data-table-card tr:hover td {
  background:#f8fafc !important;
}
.data-table-card .MuiDataGrid-footerContainer,
.data-table-card .MuiTablePagination-root {
  background:#ffffff !important;
  color:#475569 !important;
  border-top:1px solid #e5e7eb !important;
}
@media (max-width:1280px) {
  .dashboard-shell { grid-template-columns:1fr; }
  .sidebar-shell { min-height:auto; padding:24px; }
  .main-shell { padding:40px 24px; }
  .data-field-grid { grid-template-columns:1fr !important; }
}
</style>

<|layout|columns=306px 1|class_name=dashboard-shell|
<|part|class_name=sidebar-column|
__SIDEBAR__
|>

<|part|class_name=main-shell|
<div class='data-management-page'>
  <div class='page-header data-header'>
    <div class='logo-shell'>
      <div class='logo-text'>AMPCUS</div>
      <div class='logo-subtext'>collaboration redefined</div>
    </div>
  </div>

  <h1 class='data-page-title'>Data Management</h1>
</div>

<|part|class_name=data-accordion-stack|
<|part|class_name=data-accordion|
<|{cycle_expander_label}|button|on_action=toggle_cycle_form|class_name=data-expander-btn|>

<|part|render={show_cycle_form}|
<|part|class_name=data-field-grid|
<|part|class_name=data-field|
<div class='data-field-label'>Cycle Name</div>
<|{cycle_name}|input|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Planned Test Cases</div>
<|{planned}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Executed Test Cases</div>
<|{executed}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Passed Test Cases</div>
<|{passed}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Failed Test Cases</div>
<|{failed}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Blocked Test Cases</div>
<|{blocked}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Deferred Test Cases</div>
<|{deferred}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Scope Executed %</div>
<|{scope_executed}|number|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Scope Pending %</div>
<|{scope_pending}|number|>
|>
|>

<|Save Cycle|button|on_action=add_cycle|class_name=data-primary-btn|>
|>
|>

<|part|class_name=data-accordion|
<|{defect_expander_label}|button|on_action=toggle_defect_form|class_name=data-expander-btn|>

<|part|render={show_defect_form}|
<|part|class_name=data-field-grid|
<|part|class_name=data-field|
<div class='data-field-label'>Defect ID</div>
<|{defect_id}|input|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Cycle</div>
<|{cycle_selected}|selector|lov={cycle_options}|dropdown=True|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Scenario ID</div>
<|{scenario_id}|input|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Testcase ID</div>
<|{testcase_id}|input|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Severity</div>
<|{severity}|selector|lov={severity_options}|dropdown=True|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Status</div>
<|{status}|selector|lov={status_options}|dropdown=True|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Root Cause</div>
<|{root_cause}|selector|lov={root_cause_options}|dropdown=True|>
|>
<|part|class_name=data-field|
<div class='data-field-label'>Discovered Week</div>
<|{week}|input|>
|>
|>

<|Save Defect|button|on_action=add_defect|class_name=data-primary-btn|>
|>
|>
|>

<|part|class_name=data-management-page|
<div class='data-section-title'>Current data</div>

<|part|class_name=data-table-card|
<div class='data-table-heading'>Test Execution</div>
<|{test_execution_data}|table|class_name=execution-table|>
|>

<|part|class_name=data-table-card|
<div class='data-table-heading'>Defects</div>
<|{defect_data}|table|class_name=execution-table|>
|>
|>
|>
|>
"""
data_explorer = data_explorer.replace("__SIDEBAR__", sidebar_html("data-management"))
