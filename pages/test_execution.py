import html

import pandas as pd

from components.layout import build_page_shell
from database.db import load_all_tables
from services.metrics_service import get_analytics_datasets


def html_cycle_bar_chart(data, metric, title, y_title):
    if data.empty:
        return "<div class='empty-chart'>No data available for chart.</div>"

    chart_data = data.sort_values(metric, ascending=False)
    colors = ["#0b6fc6", "#7ec2f3", "#ff2931", "#ffa3a8"]
    bars = []
    for idx, row in chart_data.reset_index(drop=True).iterrows():
        value = float(row[metric])
        label = html.escape(str(row["cycle_name"]))
        text_color = "#ffffff" if idx in (0, 2) else "#1f2937"
        bars.append(
            f"""
            <div class='css-bar-item'>
              <div class='css-bar-track'>
                <div class='css-bar' style='height:{max(4, min(value, 100))}%; background:{colors[idx % len(colors)]};'>
                  <span style='color:{text_color};'>{value:.1f}%</span>
                </div>
              </div>
              <div class='css-bar-label'>{label}</div>
            </div>
            """
        )

    return f"""
    <div class='css-chart'>
      <h3>{html.escape(title)}</h3>
      <div class='css-chart-body'>
        <div class='css-y-axis'>{html.escape(y_title)}</div>
        <div class='css-bars'>{''.join(bars)}</div>
      </div>
      <div class='css-x-axis'>cycle_name</div>
    </div>
    """


def render_test_execution():
    try:
        data = load_all_tables()
    except Exception:
        data = {}

    test_execution_df = get_analytics_datasets(data).get("test_execution_by_cycle", pd.DataFrame())
    execution_chart = html_cycle_bar_chart(test_execution_df, "execution_pct", "Test Execution by Cycle", "execution_pct")
    pass_rate_chart = html_cycle_bar_chart(test_execution_df, "pass_rate_pct", "Pass Rate by Cycle", "pass_rate_pct")
    test_execution_table = test_execution_df.to_html(index=True, classes="data-table", border=0)

    page_body = f"""
<div class='page-header execution-header'>
  <div class='logo-shell ampcus-logo'>
    <div class='logo-text'>AMPCUS</div>
    <div class='logo-subtext'>collaboration redefined</div>
  </div>
  <h1 class='page-title execution-title'>Test Execution and Pass Rate</h1>
</div>

<div class='execution-chart-grid'>
  <div class='panel'>{execution_chart}</div>
  <div class='panel'>{pass_rate_chart}</div>
</div>

<div class='execution-table'>
  {test_execution_table}
</div>

<style>
.execution-header {{
  justify-items: center;
  gap: 34px;
  margin-bottom: 4px;
}}
.ampcus-logo {{
  transform: translateX(8px);
}}
.execution-title {{
  justify-self: start;
  font-size: 2.6rem;
  margin-top: 8px;
}}
.execution-chart-grid .panel {{
  min-width: 0;
}}
</style>
"""

    return build_page_shell(page_body, "test-execution")


test_execution_partial = None
test_execution = "<|part|partial={test_execution_partial}|>"
