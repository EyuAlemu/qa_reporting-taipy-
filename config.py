import os
from pathlib import Path

# App configuration
APP_TITLE = "AMPCUS   QA Reporting Dashboard"

# Database path
DB_PATH = Path(__file__).parent / "database" / "metrics.db"

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
ANALYSIS_TEMPERATURE = 0.2
CHAT_TEMPERATURE = 0.3