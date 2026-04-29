import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from taipy.gui import Gui

def create_bar_chart(data, x, y, title):
    """Create a bar chart using Plotly."""
    if data.empty:
        return "No data available for chart."
    fig = px.bar(data, x=x, y=y, title=title)
    return fig

def create_pie_chart(data, names, values, title):
    """Create a pie chart using Plotly."""
    if data.empty:
        return "No data available for chart."
    fig = px.pie(data, names=names, values=values, title=title)
    return fig

def create_line_chart(data, x, y, title):
    """Create a line chart using Plotly."""
    if data.empty:
        return "No data available for chart."
    fig = px.line(data, x=x, y=y, title=title)
    return fig

def create_gauge_chart(value, title, max_value=100):
    """Create a gauge chart using Plotly."""
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value*0.5], 'color': "lightgray"},
                {'range': [max_value*0.5, max_value], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value*0.8
            }
        }
    )])
    fig.update_layout(height=300)
    return fig

def create_merged_scope_donut(executed_pct, pending_pct, title="Scope Coverage"):
    """Create a merged donut chart for Scope Coverage."""
    labels = ['Executed', 'Pending']
    values = [executed_pct, pending_pct]
    colors = ['#0ea5e9', '#fb923c']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textposition='inside',
        textinfo='percent',
        hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'
    )])
    
    fig.update_layout(
        title=title,
        height=300,
        showlegend=True,
        font=dict(size=12)
    )
    return fig

def create_stacked_bar_chart(data, x, y, color, title):
    """Create a stacked bar chart using Plotly."""
    if data.empty:
        return "No data available for chart."
    fig = px.bar(data, x=x, y=y, color=color, title=title, barmode='stack')
    return fig

def create_horizontal_bar_chart(data, x, y, title):
    """Create a horizontal bar chart using Plotly."""
    if data.empty:
        return "No data available for chart."
    fig = px.barh(data, x=x, y=y, title=title)
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    return fig
