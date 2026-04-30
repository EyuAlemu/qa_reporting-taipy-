import sqlite3

import pandas as pd

from config import DB_PATH

def get_db_connection():
    """Get SQLite database connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)

def get_table_names():
    """Dynamically fetch all table names from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def _validate_table_name(table_name):
    table_name = str(table_name or "")
    if table_name not in get_table_names():
        raise ValueError(f"Unknown table name: {table_name}")
    return table_name

def load_all_tables():
    """Load all tables into a dictionary of pandas DataFrames."""
    tables = get_table_names()
    data = {}
    conn = get_db_connection()
    for table in tables:
        try:
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
            data[table] = df
        except Exception as e:
            print(f"Error loading table {table}: {e}")
    conn.close()
    return data

def find_column(df, possible_names):
    """Find the first matching column name from possible names."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None



def read_table(table_name):
    table_name = _validate_table_name(table_name)
    conn = get_db_connection()
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    finally:
        conn.close()
