"""
AMPCUS QA Reporting Dashboard - Main Application Entry Point
Built with Taipy GUI Framework
"""

import os
import shutil
import socket
from pathlib import Path

from taipy.gui import Gui

from config import APP_TITLE
from components.layout import (
    ask_sidebar_question,
    clear_sidebar_chat,
    sidebar_chat_history,
    sidebar_question,
)


if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY environment variable not set.")
    print("   Set it with: set OPENAI_API_KEY=your_key_here")


def clear_local_python_cache():
    for cache_dir in Path(__file__).parent.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)


clear_local_python_cache()

from pages.ai_chat import (
    ai_chat,
    ai_chat_bot,
    analysis_loading,
    analysis_tab_class,
    analysis_output,
    analysis_status_text,
    ask_question,
    chat_history,
    chat_question,
    clear_chat,
    generate_analysis,
    insight_tab_class,
    open_ai_analysis,
    open_insight_bot,
    show_analysis,
    show_insight,
)
from pages.data_explorer import (
    add_cycle,
    add_defect,
    blocked,
    cycle_expander_label,
    cycle_name,
    cycle_options,
    cycle_selected,
    defect_data,
    defect_expander_label,
    defect_id,
    data_explorer,
    deferred,
    executed,
    failed,
    passed,
    planned,
    refresh_data,
    root_cause,
    root_cause_options,
    scenario_id,
    scope_executed,
    scope_pending,
    severity,
    severity_options,
    status,
    status_options,
    testcase_id,
    test_execution_data,
    show_cycle_form,
    show_defect_form,
    toggle_cycle_form,
    toggle_defect_form,
    week,
)
from pages.defect_analytics import defect_analytics, defect_analytics_partial, render_defect_analytics
from pages.executive_overview import executive_overview, executive_overview_partial, render_executive_overview
from pages.test_execution import render_test_execution, test_execution, test_execution_partial


pages = {
    "executive-overview": executive_overview,
    "test-execution": test_execution,
    "defect-analytics": defect_analytics,
    "data-management": data_explorer,
    "ai-insights-chat": ai_chat,
    "ai-insights-chat-bot": ai_chat_bot,
    "home": executive_overview,
    "data-explorer": data_explorer,
}


def find_available_port(start_port=5000, host="127.0.0.1"):
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) != 0:
                return port
        port += 1
    raise RuntimeError(f"No available port found from {start_port} to {start_port + 49}.")


def refresh_dashboard_partials(state):
    if getattr(state, "executive_overview_partial", None):
        state.executive_overview_partial.update_content(state, render_executive_overview())
    if getattr(state, "test_execution_partial", None):
        state.test_execution_partial.update_content(state, render_test_execution())
    if getattr(state, "defect_analytics_partial", None):
        state.defect_analytics_partial.update_content(state, render_defect_analytics())


def on_navigate(state, page_name, params=None):
    if page_name in ("executive-overview", "home", "test-execution", "defect-analytics"):
        refresh_dashboard_partials(state)
    return page_name


if __name__ == "__main__":
    host = "127.0.0.1"
    port = find_available_port(5000, host)
    print("Running updated app: plain HTML sidebar, no Taipy button tags, single page shell.")
    print(f"Starting {APP_TITLE} at http://{host}:{port}/executive-overview")

    gui = Gui(pages=pages)
    executive_overview_partial = gui.add_partial(render_executive_overview())
    test_execution_partial = gui.add_partial(render_test_execution())
    defect_analytics_partial = gui.add_partial(render_defect_analytics())
    gui.run(
        title=APP_TITLE,
        debug=False,
        port=port,
        host=host,
        margin="0px",
    )
