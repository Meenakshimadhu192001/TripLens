import os
import sqlite3
import chromadb


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(
    BASE_DIR,
    "database",
    "triplens.db"
)

CHROMA_PATH = os.path.join(
    BASE_DIR,
    "database",
    "chroma_db"
)


# --------------------------------------------------
# CHROMA CLIENT
# --------------------------------------------------



chroma_client = chromadb.HttpClient(
    host="localhost",
    port=8000,
    settings=chromadb.Settings(anonymized_telemetry=False)
)

collection = chroma_client.get_or_create_collection(
    name="travel_packages",
    embedding_function=None

    
)


# --------------------------------------------------
# GET PACKAGE DATA FROM SQLITE
# --------------------------------------------------

def get_package_document(package_id):

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # Main package
    package = cursor.execute(
        """
        SELECT *
        FROM packages
        WHERE package_id = ?
        """,
        (package_id,)
    ).fetchone()

    if package is None:
        conn.close()
        return None

    # Itinerary
    itinerary = cursor.execute(
        """
        SELECT *
        FROM itinerary_days
        WHERE package_id = ?
        ORDER BY day_number
        """,
        (package_id,)
    ).fetchall()

    # Accommodation
    accommodation = cursor.execute(
        """
        SELECT *
        FROM accommodation
        WHERE package_id = ?
        """,
        (package_id,)
    ).fetchall()

    # Inclusions
    inclusions = cursor.execute(
        """
        SELECT inclusion_item
        FROM inclusions
        WHERE package_id = ?
        """,
        (package_id,)
    ).fetchall()

    # Exclusions
    exclusions = cursor.execute(
        """
        SELECT exclusion_item
        FROM exclusions
        WHERE package_id = ?
        """,
        (package_id,)
    ).fetchall()

    conn.close()

    # --------------------------------------------------
    # BUILD SEARCHABLE DOCUMENT
    # --------------------------------------------------

    document = f"""
    Package ID: {package["package_id"]}
    Agency: {package["agency_name"]}
    Package Name: {package["package_name"]}
    Destination: {package["destinations"]}
    Start Location: {package["start_location"]}
    Duration: {package["duration_days"]} days / {package["duration_nights"]} nights
    Price: {package["price"]}
    Transport: {package["transport_type"]}
    Theme: {package["theme"]}
    Suitable For: {package["suited_for"]}
    Itinerary Pace: {package["itinerary_pace"]}
    Customizable: {package["customizable"]}

    ITINERARY:
    """

    for day in itinerary:
        document += f"""
    Day {day["day_number"]}:
    Stops: {day["stops"]}
    Activities: {day["activities"]}
    Activity Type: {day["activity_type"]}
    Distance: {day["distance_km"]} km
    Transit Time: {day["transit_hours"]} hours
    Meals: {day["meals_included_today"]}
    Notes: {day["notes"]}
    """

    document += "\nACCOMMODATION:\n"

    for hotel in accommodation:
        document += f"""
    Destination: {hotel["destination"]}
    Category: {hotel["accommodation_category"]}
    Hotel: {hotel["hotel_name"]}
    Guaranteed: {hotel["hotel_guaranteed"]}
    """

    document += "\nINCLUSIONS:\n"

    for item in inclusions:
       document += f"- {item['inclusion_item']}\n"

    document += "\nEXCLUSIONS:\n"

    for item in exclusions:
        document += f"- {item['exclusion_item']}\n"

    return document


# --------------------------------------------------
# SYNC ONE PACKAGE TO CHROMADB
# --------------------------------------------------

def sync_package(package_id):
    print("[DEBUG] sync_package entered", flush=True)

    document = get_package_document(package_id)

    print("[DEBUG] before upsert", flush=True)

    if document is None:
        print(f"[ERROR] Package not found: {package_id}")
        return

    collection.upsert(
        ids=[package_id],
        documents=[document],
        metadatas=[
            {
                "package_id": package_id
            }
        ],
        embeddings=[[0.0] * 384]
    )

    print(
        f"[CHROMA] Package synced successfully: {package_id}"
    )


# --------------------------------------------------
# SYNC ALL PACKAGES
# --------------------------------------------------

if __name__ == "__main__":

    conn = sqlite3.connect(DB_PATH)

    packages = conn.execute(
        "SELECT package_id FROM packages"
    ).fetchall()

    conn.close()

    print(f"[INFO] Total packages found: {len(packages)}")

    for package in packages:
        sync_package(package[0])

    print("[INFO] All packages synced successfully.")