import os
import sqlite3
import time

from chroma_sync import sync_package


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
# PROCESS PENDING QUEUE
# --------------------------------------------------

def process_queue():

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT id, package_id
        FROM sync_queue
        WHERE status = 'pending'
        ORDER BY id
    """).fetchall()

    for queue_id, package_id in rows:

        try:
            print(
                f"[QUEUE] Syncing package: {package_id}"
            )

            sync_package(package_id)

            conn.execute("""
                UPDATE sync_queue
                SET status = 'done',
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (queue_id,))

            conn.commit()

            print(
                f"[QUEUE] Completed: {package_id}"
            )

        except Exception as e:

            print(
                f"[ERROR] Failed: {package_id} -> {e}"
            )

    conn.close()


# --------------------------------------------------
# WORKER
# --------------------------------------------------

if __name__ == "__main__":

    print("TripLens DB Sync Worker started...")

    while True:

        process_queue()

        time.sleep(5)