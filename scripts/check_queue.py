import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "triplens.db")

conn = sqlite3.connect(DB_PATH)

rows = conn.execute("""
SELECT id, package_id, status, created_at, processed_at
FROM sync_queue
ORDER BY id DESC
LIMIT 10
""").fetchall()

print("Sync queue:")

for row in rows:
    print(row)

conn.close()