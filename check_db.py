import sqlite3
import pandas as pd
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "database" / "metrics.db"

def check_database():
    if not DB_PATH.exists():
        print(f"Database file not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print('Tables:', tables)

    for table in tables:
        if table == 'sqlite_sequence':
            continue
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 3", conn)
            print(f"\n{table} columns: {list(df.columns)}")
            print(f"{table} sample rows: {len(df)} total")
            if not df.empty:
                print(df.head().to_dict(orient='records'))
        except Exception as e:
            print(f"Error reading {table}: {e}")

    conn.close()

if __name__ == "__main__":
    check_database()