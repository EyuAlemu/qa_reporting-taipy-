import html
from urllib.parse import quote

import pandas as pd

from components.layout import build_page_shell
from database.db import load_all_tables


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

def _clean_status(status):
    status = str(status)
    lowered = status.strip().lower()
    if lowered in {"closed/deferred", "resolved", "closed", "deferred"}:
        return "Closed/Deferred"
    if lowered in {"fixed, in retest", "fixed in retest", "fixed", "in progress"}:
        return "Fixed, in Retest"
    return "Open"


def _defects_table(defects):
    if defects.empty:
        return "<div class='empty-chart'>No defects available.</div>"
    return defects.to_html(index=True, classes="data-table", border=0)


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
<div class='defect-chart severity-cycle-chart'>
  <h3>Defects by Severity &amp; Cycle</h3>
  <div class='defect-chart-layout'>
    <div class='defect-y-axis'>Defects</div>
    <div class='defect-y-ticks'>{tick_labels}</div>
    <div class='defect-vplot'>{''.join(groups)}</div>
    <div class='defect-legend severity-legend'>{legend}</div>
  </div>
  <div class='defect-x-axis'>Cycle</div>
</div>
"""


def error_discovery_trend(defects):
    if defects.empty:
        return "<div class='empty-chart'>No data available for chart.</div>"

    counts = defects["discovered_week"].value_counts().sort_index()
    labels = list(counts.index)
    values = [int(v) for v in counts.values]
    max_value = max(values) if values else 1
    min_value = min(values) if values else 0
    value_range = max(max_value - min_value, 1)
    points = []
    for idx, value in enumerate(values):
        x = 50 if len(values) == 1 else 8 + (idx / (len(values) - 1)) * 84
        y = 88 - (((value - min_value) / value_range) * 76)
        points.append((x, y, value))

    polyline_points = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
    markers = "".join(
        f"<circle cx='{x:.2f}' cy='{y:.2f}' r='1.6'><title>Defects: {value}</title></circle>"
        for x, y, value in points
    )
    trend_svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'>
  <polyline points='{polyline_points}' fill='none' stroke='#0b6fc6' stroke-width='1.2' stroke-linecap='round' stroke-linejoin='round' vector-effect='non-scaling-stroke'/>
  <g fill='#0b6fc6' stroke='#ffffff' stroke-width='0.7' vector-effect='non-scaling-stroke'>{markers}</g>
</svg>
"""
    trend_src = "data:image/svg+xml;charset=utf-8," + quote(trend_svg)
    labels_html = "".join(f"<span>{html.escape(str(label))}</span>" for label in labels)
    y_ticks = list(range(max_value, min_value - 1, -1))
    y_labels = "".join(f"<span>{value}</span>" for value in y_ticks)

    return f"""
<div class='defect-chart'>
  <h3>Error Discovery Trend</h3>
  <div class='line-chart-wrap'>
    <div class='line-y-axis'>Defects</div>
    <div class='line-y-labels'>{y_labels}</div>
    <div class='line-chart'><img class='line-chart-img' src='{trend_src}' alt='Error discovery trend line' /></div>
  </div>
  <div class='line-x-labels'>{labels_html}</div>
  <div class='defect-x-axis'>Week</div>
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
        total = sum(int(grouped.get((status, sev), 0)) for sev in severities)
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
<div class='defect-chart'>
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
<div class='defect-chart'>
  <h3>Defects by Root Cause</h3>
  <div class='root-chart'>{''.join(rows)}</div>
  <div class='defect-x-axis'>count</div>
</div>
"""


def render_defect_analytics():
    try:
        data = load_all_tables()
        defects_df = data.get("defects", pd.DataFrame()).copy()
    except Exception:
        defects_df = pd.DataFrame()

    page_body = f"""
<div class='page-header defect-header'>
  <div class='logo-shell'>
    <div class='logo-text'>AMPCUS</div>
    <div class='logo-subtext'>collaboration redefined</div>
  </div>
</div>

<h1 class='defect-page-title'>Defect Analytics</h1>

<div class='defect-grid'>
  <div class='panel'>{defects_by_severity_cycle(defects_df)}</div>
  <div class='panel'>{error_discovery_trend(defects_df)}</div>
  <div class='panel'>{defects_by_status_priority(defects_df)}</div>
  <div class='panel'>{defects_by_root_cause(defects_df)}</div>
</div>

<div class='execution-table defect-table'>
  {_defects_table(defects_df)}
</div>
"""

    return build_page_shell(page_body, "defect-analytics")


defect_analytics_partial = None
defect_analytics = "<|part|partial={defect_analytics_partial}|>"
