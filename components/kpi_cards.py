from taipy.gui import Gui

def create_kpi_card(title, value, icon="📊"):
    """Create a KPI card component."""
    return f"""
<div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px; text-align: center; background-color: #f9f9f9;">
    <div style="font-size: 2em;">{icon}</div>
    <h3>{title}</h3>
    <p style="font-size: 1.5em; font-weight: bold;">{value}</p>
</div>
"""

def render_kpi_cards(kpis):
    """Render all KPI cards."""
    cards = ""
    for key, value in kpis.items():
        title = key.replace('_', ' ').title()
        cards += create_kpi_card(title, value)
    return cards