import os
import sqlite3

# --------------------------------------------------
# PATH
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DB_PATH = os.path.join(
    BASE_DIR,
    "database",
    "triplens.db"
)


# --------------------------------------------------
# CREATE SYNC QUEUE + TRIGGERS
# --------------------------------------------------

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
)
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS trg_packages_after_insert
AFTER INSERT ON packages
BEGIN
    INSERT INTO sync_queue(package_id)
    VALUES (NEW.package_id);
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS trg_packages_after_update
AFTER UPDATE ON packages
BEGIN
    INSERT INTO sync_queue(package_id)
    VALUES (NEW.package_id);
END
""")

conn.commit()
conn.close()

print("Sync queue and triggers created successfully!")