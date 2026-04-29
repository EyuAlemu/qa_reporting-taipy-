from taipy.gui import Gui
from services.openai_service import analyze_qa_metrics, qa_chatbot

def create_ai_analysis_panel(context):
    """Create AI analysis panel."""
    analysis = analyze_qa_metrics(context)
    return f"""
<h3>AI Executive Analysis</h3>
<div style="border: 1px solid #ddd; padding: 16px; border-radius: 8px; background-color: #f9f9f9;">
{analysis}
</div>
"""

def create_chatbot_interface(question, context):
    """Create chatbot interface."""
    if question:
        response = qa_chatbot(question, context)
    else:
        response = "Ask me a question about the QA data!"
    return f"""
<h3>QA Chatbot</h3>
<input type="text" id="question" value="{question}" />
<button onclick="send_question()">Ask</button>
<div style="border: 1px solid #ddd; padding: 16px; border-radius: 8px; margin-top: 16px; background-color: #f9f9f9;">
{response}
</div>
"""