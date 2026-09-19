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
# INSERT TEST PACKAGE
# --------------------------------------------------

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
INSERT INTO packages (
    package_id,
    agency_name,
    package_name,
    destinations,
    start_location,
    duration_days,
    duration_nights,
    price,
    transport_type,
    theme,
    suited_for,
    itinerary_pace,
    customizable
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "TEST001",
    "TripLens Test Agency",
    "Kerala Test Package",
    "Munnar, Alleppey",
    "Kochi",
    3,
    2,
    15000,
    "Car",
    "Nature",
    "Family",
    "Relaxed",
    "Yes"
))

conn.commit()
conn.close()

print("Test package inserted successfully!")