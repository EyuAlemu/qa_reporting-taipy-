import html

import pandas as pd

from components.layout import build_page_shell
from database.db import load_all_tables
from services.metrics_service import calculate_kpis


SEVERITY_COLORS = {
    "Critical": "#ef4b4f",
    "High": "#f5666b",
    "Medium": "#fb9a66",
    "Low": "#e6dd59",
}

ROOT_CAUSE_CATEGORIES = ["Code", "Stored Proc", "UI", "Environment", "Configuration", "Database"]
STATUS_CATEGORIES = ["Open", "Fixed, in Retest", "Closed/Deferred"]

ROOT_CAUSE_COLORS = [
    "#0b6fc6",
    "#22a06b",
    "#f59e0b",
    "#8b5cf6",
    "#ef4b4f",
    "#14b8a6",
    "#f97316",
    "#64748b",
    "#d946ef",
]


def fmt_pct(value):
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return value


def fmt_int(value):
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return value


def _clean_status(status):
    status = str(status)
    lowered = status.strip().lower()
    if lowered in {"closed/deferred", "resolved", "closed", "deferred"}:
        return "Closed/Deferred"
    if lowered in {"fixed, in retest", "fixed in retest", "fixed", "in progress"}:
        return "Fixed, in Retest"
    return "Open"


def severity_stats(kpis):
    rows = [
        ("Critical", "critical_defects"),
        ("High", "high_defects"),
        ("Medium", "medium_defects"),
        ("Low", "low_defects"),
    ]
    return "".join(
        f"<div class='overview-severity' style='color:{SEVERITY_COLORS[label]};'>{label}: {fmt_int(kpis.get(key, 0))}</div>"
        for label, key in rows
    )


def error_gauge(value):
    value = max(0, min(float(value or 0), 100))
    angle = -90 + (value / 100) * 180
    return f"""
<div class='overview-gauge'>
  <div class='gauge-arc'>
    <div class='gauge-needle' style='transform:rotate({angle}deg);'></div>
    <div class='gauge-center'>{value:.0f}%</div>
    <span class='gauge-min'>0</span>
    <span class='gauge-mid'>50</span>
    <span class='gauge-max'>100</span>
  </div>
</div>
"""


def scope_donut(value):
    value = max(0, min(float(value or 0), 100))
    pending = 100 - value
    return f"""
<div class='scope-wrap'>
  <div class='scope-donut' style='background:conic-gradient(#1378ca 0 {value}%, #fb9a66 {value}% 100%);'>
    <span class='scope-slice-label scope-executed-label'>{value:.0f}%</span>
    <span class='scope-slice-label scope-pending-label'>{pending:.0f}%</span>
    <div class='scope-hole'>
      <strong>{value:.1f}%</strong>
      <span>Executed</span>
    </div>
  </div>
  <div class='scope-legend'>
    <div><span style='background:#1378ca;'></span>Executed</div>
    <div><span style='background:#fb9a66;'></span>Pending</div>
  </div>
</div>
"""


def defects_by_severity_cycle(defects):
    if defects.empty:
        return "<div class='empty-chart'>No data available for chart.</div>"

    cycles = sorted(defects["cycle_name"].dropna().unique())
    severities = ["Critical", "High", "Medium", "Low"]
    grouped = defects.groupby(["cycle_name", "severity"]).size()
    max_count = max(int(grouped.max()), 1)
    tick_step = 1 if max_count <= 5 else max(1, round(max_count / 4))
    ticks = list(range(max_count, -1, -tick_step))
    if ticks[-1] != 0:
        ticks.append(0)
    tick_labels = "".join(f"<span>{tick}</span>" for tick in ticks)

    groups = []
    for cycle in cycles:
        bars = []
        for severity in severities:
            count = int(grouped.get((cycle, severity), 0))
            height = 0 if count == 0 else (count / max_count) * 100
            bars.append(
                f"<div class='defect-vbar' title='{severity}: {count}' "
                f"style='height:{height}%; background:{SEVERITY_COLORS[severity]};'></div>"
            )
        groups.append(
            f"""
<div class='defect-vgroup'>
  <div class='defect-vbars'>{''.join(bars)}</div>
  <div class='defect-axis-label'>{html.escape(cycle)}</div>
</div>
"""
        )

    legend = "".join(
        f"<div><span style='background:{color};'></span>{severity}</div>"
        for severity, color in SEVERITY_COLORS.items()
    )
    return f"""
<div class='defect-chart overview-small-chart'>
  <h3>Defects by Severity &amp; Cycle</h3>
  <div class='defect-chart-layout'>
    <div class='defect-y-axis'>Defects</div>
    <div class='defect-y-ticks'>{tick_labels}</div>
    <div class='defect-vplot'>{''.join(groups)}</div>
    <div class='defect-legend'>{legend}</div>
  </div>
  <div class='defect-x-axis'>Cycle</div>
</div>
"""


def defects_by_status_priority(defects):
    if defects.empty:
        return "<div class='empty-chart'>No data available for chart.</div>"

    work = defects.copy()
    work["status_group"] = work["status"].map(_clean_status)
    statuses = STATUS_CATEGORIES
    severities = ["Critical", "High", "Medium", "Low"]
    grouped = work.groupby(["status_group", "severity"]).size()
    max_total = max([sum(int(grouped.get((status, sev), 0)) for sev in severities) for status in statuses] + [1])

    rows = []
    for status in statuses:
        segments = []
        for severity in severities:
            count = int(grouped.get((status, severity), 0))
            if count == 0:
                continue
            width = (count / max_total) * 100
            segments.append(
                f"<div class='status-segment' style='width:{width}%; background:{SEVERITY_COLORS[severity]};'>{count}</div>"
            )
        rows.append(
            f"""
<div class='status-row'>
  <div class='status-label'>{html.escape(status)}</div>
  <div class='status-track'>{''.join(segments)}</div>
</div>
"""
        )

    legend = "".join(
        f"<div><span style='background:{color};'></span>{severity}</div>"
        for severity, color in SEVERITY_COLORS.items()
    )
    return f"""
<div class='defect-chart overview-small-chart'>
  <h3>Defects by Status &amp; Priority</h3>
  <div class='status-chart'>
    <div class='status-rows'>{''.join(rows)}</div>
    <div class='defect-legend'>{legend}</div>
  </div>
  <div class='defect-x-axis'>Defects</div>
</div>
"""


def defects_by_root_cause(defects):
    counts = (
        defects["root_cause"].value_counts()
        if not defects.empty and "root_cause" in defects.columns
        else pd.Series(dtype="int64")
    ).reindex(ROOT_CAUSE_CATEGORIES, fill_value=0)
    max_count = max(int(counts.max()), 1)
    rows = []
    for idx, (label, value) in enumerate(counts.items()):
        width = (int(value) / max_count) * 100
        color = ROOT_CAUSE_COLORS[idx % len(ROOT_CAUSE_COLORS)]
        zero_class = " root-zero" if int(value) == 0 else ""
        zero_count = "<span class='root-zero-count'>0</span>" if int(value) == 0 else ""
        rows.append(
            f"""
<div class='root-row'>
  <div class='root-label'>{html.escape(str(label))}</div>
  <div class='root-track'><div class='root-fill{zero_class}' style='width:{width}%; background:{color};'>{'' if int(value) == 0 else int(value)}</div>{zero_count}</div>
</div>
"""
        )
    return f"""
<div class='defect-chart overview-small-chart'>
  <h3>Defects by Root Cause</h3>
  <div class='root-chart'>{''.join(rows)}</div>
  <div class='defect-x-axis'>count</div>
</div>
"""


def alert_cards(alerts):
    if alerts.empty:
        return "<div class='empty-chart'>No active alerts.</div>"

    cards = []
    for _, row in alerts.head(3).iterrows():
        priority = str(row.get("priority", "")).lower()
        style_class = "alert-high" if priority == "high" else "alert-medium"
        cards.append(f"<div class='alert-card {style_class}'>{html.escape(str(row.get('message', '')))}</div>")
    return "".join(cards)


try:
    data = load_all_tables()
    kpis = calculate_kpis(data)
except Exception:
    data = {}
    kpis = {}

defects_df = data.get("defects", pd.DataFrame()).copy()
alerts_df = data.get("alerts", pd.DataFrame()).copy()
if not alerts_df.empty and "is_active" in alerts_df.columns:
    alerts_df = alerts_df[alerts_df["is_active"].astype(str).str.upper().eq("Y")]

base_html = f"""
<div class='page-header overview-header'>
  <div class='logo-shell'>
    <div class='logo-text'>AMPCUS</div>
    <div class='logo-subtext'>collaboration redefined</div>
  </div>
</div>

<h1 class='overview-title'>AMPCUS Program Functional Testing Dashboard Overview</h1>
<div class='overview-date'>As of {pd.Timestamp.now().strftime('%m/%d/%Y')}</div>

<div class='overview-top-grid'>
  <div class='overview-metric'>
    <div class='overview-label'>Test Execution %</div>
    <div class='overview-big'>{fmt_pct(kpis.get('execution_rate_pct', 0))}</div>
    <div class='overview-note'>Executed: {fmt_int(kpis.get('executed_test_cases', 0))} / {fmt_int(kpis.get('total_test_cases', 0))}</div>
  </div>
  <div class='overview-metric'>
    <div class='overview-label'>Pass %</div>
    <div class='overview-big'>{fmt_pct(kpis.get('pass_rate_pct', 0))}</div>
    <div class='overview-note'>Passed / Executed</div>
  </div>
  <div class='overview-defects'>
    <h3>Defect Stats</h3>
    {severity_stats(kpis)}
  </div>
  <div class='overview-summary'>
    <div>
      <div class='overview-label'>Closed Defects</div>
      <div class='overview-big small'>{fmt_int(kpis.get('closed_defects', 0))}</div>
    </div>
    <div>
      <div class='overview-label'>Deferred Tests</div>
      <div class='overview-big small'>{fmt_int(kpis.get('deferred_tests', 0))}</div>
    </div>
  </div>
</div>

<div class='overview-chart-row'>
  <div class='panel'>
    <h3 class='overview-chart-title'>Error Discovery Rate</h3>
    {error_gauge(kpis.get('error_discovery_rate_pct', 0))}
  </div>
  <div class='panel'>
    <h3 class='overview-chart-title'>Scope Coverage</h3>
    {scope_donut(kpis.get('scope_coverage_pct', 0))}
  </div>
  <div class='panel'>
    {defects_by_severity_cycle(defects_df)}
  </div>
</div>

<div class='overview-bottom-row'>
  <div class='panel'>{defects_by_status_priority(defects_df)}</div>
  <div class='panel'>{defects_by_root_cause(defects_df)}</div>
  <div class='panel'>
    <h2 class='alerts-title'>Alerts</h2>
    <div class='alerts-list'>{alert_cards(alerts_df)}</div>
  </div>
</div>
"""

executive_overview = build_page_shell(base_html, "executive-overview")
