
import os
import sys
from dotenv import load_dotenv
import psycopg2

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

load_dotenv("backend/.env")

def list_conflicts():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("SELECT id, started_at, status FROM conflicts ORDER BY started_at DESC LIMIT 5;")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} conflicts:")
        for row in rows:
            print(f"ID: {row[0]}, Started: {row[1]}, Status: {row[2]}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_conflicts()
