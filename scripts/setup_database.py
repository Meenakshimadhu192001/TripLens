import os
import sqlite3
import pandas as pd

# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(BASE_DIR, "database", "triplens.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "Package_Details_India(final).xlsx")


# --------------------------------------------------
# CHECK EXCEL FILE
# --------------------------------------------------

if not os.path.exists(EXCEL_PATH):
    raise FileNotFoundError(
        f"Excel file not found:\n{EXCEL_PATH}"
    )

print(f"[INGESTION] Reading Excel file:")
print(EXCEL_PATH)


# --------------------------------------------------
# CONNECT TO SQLITE
# --------------------------------------------------

conn = sqlite3.connect(DB_PATH)

# Enable foreign-key relationships
conn.execute("PRAGMA foreign_keys = ON;")


# --------------------------------------------------
# CREATE TABLES FROM schema.sql
# --------------------------------------------------

with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
    schema_sql = file.read()

conn.executescript(schema_sql)

print("[DATABASE] Tables created successfully.")


# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def clean_text(value):
    """Convert empty/NaN values to None."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def clean_number(value):
    """Convert price/duration values into numbers."""
    if pd.isna(value):
        return None

    try:
        value = str(value).replace(",", "").replace("₹", "").strip()

        # Handle values such as '5 days'
        number = ""
        for char in value:
            if char.isdigit() or char == ".":
                number += char
            else:
                if number:
                    break

        return float(number) if number else None

    except Exception:
        return None


# --------------------------------------------------
# READ EXCEL WORKBOOK
# --------------------------------------------------

excel = pd.ExcelFile(EXCEL_PATH)

print("\n[EXCEL] Sheets found:")
print(excel.sheet_names)


# --------------------------------------------------
# 1. PACKAGES
# --------------------------------------------------

df = pd.read_excel(excel, sheet_name="Packages")

print(f"\n[PACKAGES] Original records: {len(df)}")

# Remove completely empty rows
df = df.dropna(how="all")

# Clean column names
df.columns = df.columns.str.strip()

# Handle Excel spelling mistake
if "cutomizable" in df.columns:
    df = df.rename(columns={"cutomizable": "customizable"})

# Keep only rows having package_id
df = df.dropna(subset=["package_id"])

# Convert package_id to clean text
df["package_id"] = df["package_id"].astype(str).str.strip()

# Remove duplicate package IDs
df = df.drop_duplicates(subset=["package_id"])

# Clean numeric fields
for column in [
    "duration_days",
    "duration_nights",
    "price",
    "list_price"
]:
    if column in df.columns:
        df[column] = df[column].apply(clean_number)

package_columns = [
    "package_id",
    "agency_name",
    "package_name",
    "source_url_or_doc",
    "data_source",
    "destinations",
    "start_location",
    "duration_days",
    "duration_nights",
    "price",
    "list_price",
    "tier_range_exists",
    "transport_type",
    "theme",
    "suited_for",
    "itinerary_pace",
    "customizable",
    "agency_contact"
]

# Add missing columns as None
for column in package_columns:
    if column not in df.columns:
        df[column] = None

df_packages = df[package_columns].copy()

# Clean text columns
for column in package_columns:
    if column not in [
        "duration_days",
        "duration_nights",
        "price",
        "list_price"
    ]:
        df_packages[column] = df_packages[column].apply(clean_text)


# Insert into SQLite
df_packages.to_sql(
    "packages",
    conn,
    if_exists="append",
    index=False
)

print(f"[PACKAGES] Inserted: {len(df_packages)}")


# Valid package IDs
valid_package_ids = set(df_packages["package_id"])


# --------------------------------------------------
# 2. ITINERARY DAYS
# --------------------------------------------------

df = pd.read_excel(
    excel,
    sheet_name="Itinerary_Days"
)

df.columns = df.columns.str.strip()

df = df.dropna(subset=["package_id"])

df["package_id"] = df["package_id"].astype(str).str.strip()

# Keep only packages that exist in packages table
df = df[df["package_id"].isin(valid_package_ids)]

for column in [
    "day_number",
    "distance_km",
    "transit_hours",
    "stops_requiring_separate_drives"
]:
    if column in df.columns:
        df[column] = df[column].apply(clean_number)

itinerary_columns = [
    "package_id",
    "day_number",
    "stops",
    "activities",
    "activity_type",
    "distance_km",
    "transit_hours",
    "stops_requiring_separate_drives",
    "meals_included_today",
    "flagged_for_verification",
    "notes"
]

for column in itinerary_columns:
    if column not in df.columns:
        df[column] = None

df_itinerary = df[itinerary_columns].copy()

df_itinerary.to_sql(
    "itinerary_days",
    conn,
    if_exists="append",
    index=False
)

print(f"[ITINERARY] Inserted: {len(df_itinerary)}")


# --------------------------------------------------
# 3. ACCOMMODATION
# --------------------------------------------------

df = pd.read_excel(
    excel,
    sheet_name="Accommodation"
)

df.columns = df.columns.str.strip()

df = df.dropna(subset=["package_id"])

df["package_id"] = df["package_id"].astype(str).str.strip()

df = df[df["package_id"].isin(valid_package_ids)]

accommodation_columns = [
    "package_id",
    "destination",
    "accommodation_category",
    "hotel_name",
    "hotel_guaranteed"
]

for column in accommodation_columns:
    if column not in df.columns:
        df[column] = None

df_accommodation = df[accommodation_columns].copy()

df_accommodation.to_sql(
    "accommodation",
    conn,
    if_exists="append",
    index=False
)

print(f"[ACCOMMODATION] Inserted: {len(df_accommodation)}")


# --------------------------------------------------
# 4. INCLUSIONS
# --------------------------------------------------

df = pd.read_excel(
    excel,
    sheet_name="Inclusions"
)

df.columns = df.columns.str.strip()

df = df.dropna(subset=["package_id"])

df["package_id"] = df["package_id"].astype(str).str.strip()

df = df[df["package_id"].isin(valid_package_ids)]

if "inclusion_item" not in df.columns:
    raise ValueError(
        "Column 'inclusion_item' not found in Inclusions sheet."
    )

df_inclusions = df[
    ["package_id", "inclusion_item"]
].copy()

df_inclusions.to_sql(
    "inclusions",
    conn,
    if_exists="append",
    index=False
)

print(f"[INCLUSIONS] Inserted: {len(df_inclusions)}")


# --------------------------------------------------
# 5. EXCLUSIONS
# --------------------------------------------------

df = pd.read_excel(
    excel,
    sheet_name="Exclusions"
)

df.columns = df.columns.str.strip()

df = df.dropna(subset=["package_id"])

df["package_id"] = df["package_id"].astype(str).str.strip()

df = df[df["package_id"].isin(valid_package_ids)]

if "exclusion_item" not in df.columns:
    raise ValueError(
        "Column 'exclusion_item' not found in Exclusions sheet."
    )

df_exclusions = df[
    ["package_id", "exclusion_item"]
].copy()

df_exclusions.to_sql(
    "exclusions",
    conn,
    if_exists="append",
    index=False
)

print(f"[EXCLUSIONS] Inserted: {len(df_exclusions)}")


# --------------------------------------------------
# COMMIT
# --------------------------------------------------

conn.commit()

# Check database tables
cursor = conn.cursor()

print("\n" + "=" * 50)
print("DATABASE INGESTION COMPLETED")
print("=" * 50)

tables = [
    "packages",
    "itinerary_days",
    "accommodation",
    "inclusions",
    "exclusions"
]

for table in tables:
    count = cursor.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"{table}: {count} records")

conn.close()

print("\n[SUCCESS] Excel data successfully loaded into SQLite.")