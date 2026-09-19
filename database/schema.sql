PRAGMA foreign_keys = ON;

-- 1. Main package table
CREATE TABLE IF NOT EXISTS packages (
    package_id TEXT PRIMARY KEY,
    agency_name TEXT,
    package_name TEXT,
    source_url_or_doc TEXT,
    data_source TEXT,
    destinations TEXT,
    start_location TEXT,
    duration_days INTEGER,
    duration_nights INTEGER,
    price REAL,
    list_price REAL,
    tier_range_exists TEXT,
    transport_type TEXT,
    theme TEXT,
    suited_for TEXT,
    itinerary_pace TEXT,
    customizable TEXT,
    agency_contact TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Daily itinerary details
CREATE TABLE IF NOT EXISTS itinerary_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    day_number INTEGER,
    stops TEXT,
    activities TEXT,
    activity_type TEXT,
    distance_km REAL,
    transit_hours REAL,
    stops_requiring_separate_drives INTEGER,
    meals_included_today TEXT,
    flagged_for_verification TEXT,
    notes TEXT,

    FOREIGN KEY (package_id)
        REFERENCES packages(package_id)
        ON DELETE CASCADE
);

-- 3. Accommodation details
CREATE TABLE IF NOT EXISTS accommodation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    destination TEXT,
    accommodation_category TEXT,
    hotel_name TEXT,
    hotel_guaranteed TEXT,

    FOREIGN KEY (package_id)
        REFERENCES packages(package_id)
        ON DELETE CASCADE
);

-- 4. Package inclusions
CREATE TABLE IF NOT EXISTS inclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    inclusion_item TEXT,

    FOREIGN KEY (package_id)
        REFERENCES packages(package_id)
        ON DELETE CASCADE
);

-- 5. Package exclusions
CREATE TABLE IF NOT EXISTS exclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    exclusion_item TEXT,

    FOREIGN KEY (package_id)
        REFERENCES packages(package_id)
        ON DELETE CASCADE
);