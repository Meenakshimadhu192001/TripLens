"""TripLens - NLP Preference Extraction

Deterministic first pass (regex-based).
Never invents values it cannot find.

Destinations and origin cities are dynamically detected
from the SQLite package database.
"""

import os
import re
import sqlite3
from functools import lru_cache


THEME_KEYWORDS = {
    "nature": [
        "nature", "natural", "greenery", "waterfall", "waterfalls",
        "hills", "scenic", "scenery", "landscape", "landscapes",
        "forest", "forests", "wildlife", "outdoors"
    ],
    "beach": [
        "beach", "beaches", "coast", "coastal", "island", "islands",
        "sea", "shore", "shores"
    ],
    "backwaters": [
        "backwater", "backwaters", "houseboat", "houseboats", "lagoon"
    ],
    "adventure": [
        "adventure", "adventurous", "trek", "treks", "trekking",
        "rafting", "paragliding", "camping", "camp"
    ],
    "heritage": [
        "heritage", "temple", "temples", "fort", "forts", "culture",
        "cultural", "historic", "historical", "palace", "palaces"
    ],
    "pilgrimage": [
        "pilgrimage", "spiritual", "temple visit", "shrine"
    ],
    "hill-station": [
        "hill station", "hill-stations", "mountain", "mountains", "snow",
        "valley", "valleys", "snowfall", "snowy"
    ],
    "honeymoon/romance": [
        "honeymoon", "romantic", "romance", "couple", "anniversary"
    ],
    "family": [
        "family", "families", "kids", "children", "parents", "child-friendly"
    ],
    "sightseeing": [
        "sightseeing", "sight-seeing", "points", "viewpoint", "viewpoints",
        "tourist spots", "attractions", "landmarks"
    ],
}


PACE_KEYWORDS = {
    "Relaxed": [
        "relaxed", "relaxing", "leisure", "slow", "slow-paced",
        "slow paced", "peaceful", "unrushed", "easy", "laid-back", "laid back"
    ],
    "Active": [
        "active", "packed", "fast-paced", "fast paced", "busy",
        "full circuit", "express", "intensive", "hectic"
    ],
}


DEFAULT_ORIGIN_CITIES = [
    "delhi",
    "new delhi",
    "chandigarh",
    "kochi",
    "cochin",
    "bangalore",
    "bengaluru",
    "mumbai",
    "bombay",
    "chennai",
    "madras",
    "kolkata",
    "calcutta",
    "hyderabad",
    "pune",
    "ahmedabad",
    "surat",
    "jaipur",
    "lucknow",
    "bhopal",
    "nagpur",
    "coimbatore",
    "trivandrum",
    "thiruvananthapuram",
    "kozhikode",
    "calicut",
    "amritsar",
    "ludhiana",
    "dehradun",
    "srinagar",
]


DB_PATH = os.path.join("database", "triplens.db")


@lru_cache(maxsize=1)
def load_db_destinations_and_origins(
    db_path=DB_PATH
):
    """
    Load destinations and departure cities dynamically
    from the SQLite database.
    """

    dest_dict = {}
    origin_set = set(DEFAULT_ORIGIN_CITIES)

    possible_paths = [
        db_path,
        os.path.join(
            os.path.dirname(__file__),
            "..",
            db_path
        ),
        os.path.join("..", db_path),
    ]

    actual_db = None

    for candidate in possible_paths:
        candidate = os.path.abspath(candidate)

        if os.path.exists(candidate):
            actual_db = candidate
            break

    if actual_db:
        try:
            conn = sqlite3.connect(actual_db)
            cur = conn.cursor()

            # -----------------------------
            # Package destinations
            # -----------------------------
            cur.execute(
                """
                SELECT DISTINCT destinations
                FROM packages
                WHERE destinations IS NOT NULL
                """
            )

            package_destinations = [
                row[0]
                for row in cur.fetchall()
                if row[0]
            ]

            # -----------------------------
            # Accommodation destinations
            # -----------------------------
            cur.execute(
                """
                SELECT DISTINCT destination
                FROM accommodation
                WHERE destination IS NOT NULL
                """
            )

            accommodation_destinations = [
                row[0]
                for row in cur.fetchall()
                if row[0]
            ]

            # -----------------------------
            # Package starting locations
            # -----------------------------
            cur.execute(
                """
                SELECT DISTINCT start_location
                FROM packages
                WHERE start_location IS NOT NULL
                """
            )

            db_origins = [
                row[0]
                for row in cur.fetchall()
                if row[0]
            ]

            conn.close()

            # -----------------------------
            # Build destination dictionary
            # -----------------------------
            for raw in (
                package_destinations
                + accommodation_destinations
            ):
                raw = str(raw)

                # Remove things like:
                # (3N)
                # (+2 more)
                # (optional)
                cleaned = re.sub(
                    r"\(\d+\s*N\)",
                    "",
                    raw,
                    flags=re.IGNORECASE
                )

                cleaned = re.sub(
                    r"\+\d+\s+more",
                    "",
                    cleaned,
                    flags=re.IGNORECASE
                )

                cleaned = re.sub(
                    r"\(.*?\)",
                    "",
                    cleaned
                )

                parts = re.split(
                    r"[,/;&|]+|\band\b",
                    cleaned,
                    flags=re.IGNORECASE
                )

                for part in parts:
                    part = part.strip()

                    if len(part) < 3:
                        continue

                    if part.isdigit():
                        continue

                    key = part.lower()

                    if key not in dest_dict:
                        dest_dict[key] = part

            # -----------------------------
            # Build origin set
            # -----------------------------
            for raw in db_origins:
                raw = str(raw)

                parts = re.split(
                    r"[,/;&|]+",
                    raw
                )

                for part in parts:
                    part = part.strip()

                    if len(part) >= 3:
                        if part.lower() != "not specified":
                            origin_set.add(part.lower())

        except Exception as exc:
            print(
                f"Warning: Could not load destinations "
                f"from database: {exc}"
            )

    # -----------------------------
    # Fallback destinations
    # -----------------------------
    if not dest_dict:
        fallback_destinations = [
            "Goa",
            "Kerala",
            "Himachal Pradesh",
            "Himachal",
            "Shimla",
            "Manali",
            "Kashmir",
            "Srinagar",
            "Gulmarg",
            "Pahalgam",
            "Rajasthan",
            "Jaipur",
            "Udaipur",
            "Jodhpur",
            "Jaisalmer",
            "Alleppey",
            "Munnar",
            "Wayanad",
            "Kovalam",
            "Andaman",
            "Port Blair",
            "Sikkim",
            "Gangtok",
            "Meghalaya",
            "Shillong",
            "Assam",
            "Ladakh",
            "Leh",
            "Uttarakhand",
        ]

        for destination in fallback_destinations:
            dest_dict[destination.lower()] = destination

    return dest_dict, origin_set


def _find_first_keyword_match(
    text: str,
    keyword_map: dict
):
    """
    Find the first matching keyword using word boundaries.
    """

    for label, keywords in keyword_map.items():
        for keyword in keywords:

            pattern = rf"\b{re.escape(keyword)}\b"

            if re.search(pattern, text):
                return label

    return None


def _parse_amount(raw: str) -> int | None:
    """
    Convert a budget amount to integer rupees.

    Supported:
        20000
        20,000
        20k
        20.5k
        ₹20000
        ₹20,000
        ₹20k
        rs 20000
        rs. 20,000
        inr 20000
    """

    if not raw:
        return None

    value = str(raw).strip().lower()

    # Remove currency symbols/prefixes
    value = re.sub(
        r"^(?:₹|rs\.?|inr)\s*",
        "",
        value
    ).strip()

    # Remove spaces before k
    value = re.sub(
        r"\s*k\b",
        "k",
        value
    )

    try:

        # Example:
        # 20k
        # 20.5k
        if value.endswith("k"):

            number = value[:-1].strip()

            if not re.fullmatch(
                r"\d+(?:\.\d+)?",
                number
            ):
                return None

            return int(float(number) * 1000)

        # Example:
        # 20,000
        # 30000
        value = value.replace(",", "")

        match = re.fullmatch(
            r"\d+(?:\.\d+)?",
            value
        )

        if not match:
            return None

        return int(float(value))

    except (ValueError, TypeError):
        return None


def _normalise_city(city: str) -> str:
    """
    Normalize common city aliases.
    """

    city = city.strip().title()

    aliases = {
        "Bengaluru": "Bangalore",
        "Cochin": "Kochi",
        "Bombay": "Mumbai",
        "Madras": "Chennai",
        "Calcutta": "Kolkata",
        "Calicut": "Kozhikode",
        "Trivandrum": "Thiruvananthapuram",
    }

    return aliases.get(city, city)


def _find_destination_in_text(
    text: str,
    dest_dict: dict,
    start_location: str | None
):
    """
    Dynamically detect destination.

    Priority:
    1. Explicit "to <destination>"
    2. "<destination> trip/tour/package/holiday"
    3. Any destination existing in DB

    The origin location is excluded.
    """

    destination_keys = sorted(
        dest_dict.keys(),
        key=len,
        reverse=True
    )

    start_lower = (
        start_location.lower()
        if start_location
        else ""
    )

    # ---------------------------------------
    # 1. Explicit "to <destination>"
    # ---------------------------------------
    to_match = re.search(
        r"\bto\s+(.+?)(?=\s+(?:from|for|with|under|below|within|budget|"
        r"on|in)\b|[,.;]|$)",
        text,
        flags=re.IGNORECASE
    )

    if to_match:

        candidate_text = (
            to_match.group(1)
            .strip()
            .lower()
        )

        for destination in destination_keys:

            if destination == start_lower:
                continue

            pattern = (
                rf"\b{re.escape(destination)}\b"
            )

            if re.search(
                pattern,
                candidate_text,
                flags=re.IGNORECASE
            ):
                return dest_dict[destination]

        # Preserve an explicit but unknown destination so callers can
        # explain that it is unavailable instead of searching all packages.
        unknown_destination = re.sub(
            r"^(?:a|an|the)\s+",
            "",
            candidate_text,
            flags=re.IGNORECASE,
        ).strip()
        if unknown_destination:
            return unknown_destination.title()

    # ---------------------------------------
    # 2. "<destination> trip/tour/package"
    # ---------------------------------------
    trip_match = re.search(
        r"\b(.+?)\s+"
        r"(?:trip|tour|package|holiday|getaway|"
        r"circuit|escape|escapes)\b",
        text,
        flags=re.IGNORECASE
    )

    if trip_match:

        candidate_text = (
            trip_match.group(1)
            .strip()
            .lower()
        )

        for destination in destination_keys:

            if destination == start_lower:
                continue

            pattern = (
                rf"\b{re.escape(destination)}\b"
            )

            if re.search(
                pattern,
                candidate_text,
                flags=re.IGNORECASE
            ):
                return dest_dict[destination]

        unknown_trip_match = re.search(
            r"\b(?:plan|book|find|need|want)\s+"
            r"(?:a|an|the)?\s*"
            r"([a-z][a-z\s]{1,40}?)\s+"
            r"(?:trip|tour|package|holiday|getaway|circuit|escape|escapes)\b",
            text,
            flags=re.IGNORECASE,
        )
        if unknown_trip_match:
            return unknown_trip_match.group(1).strip().title()

    # ---------------------------------------
    # 3. Full database destination scan
    # ---------------------------------------
    for destination in destination_keys:

        if destination == start_lower:
            continue

        pattern = (
            rf"\b{re.escape(destination)}\b"
        )

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            return dest_dict[destination]

    return None


def extract_preferences(
    prompt_text: str
) -> dict:

    text = str(prompt_text or "").lower()

    prefs = {
        "destination_region": None,
        "destination_known": True,
        "start_location": None,
        "duration_days": None,
        "budget_min": None,
        "budget_max": None,
        "travelers": None,
        "pace": None,
        "interests": [],
    }

    dest_dict, origin_set = (
        load_db_destinations_and_origins()
    )

    # =========================================================
    # 1. BUDGET
    # =========================================================

    # Amount examples:
    #
    # ₹30,000
    # 30000
    # 30k
    # ₹30k
    # 20.5k
    #
    AMOUNT_PATTERN = (
        r"(?:₹\s*|rs\.?\s*|inr\s*)?"
        r"(?:"
        r"\d+(?:\.\d+)?\s*[kK]"
        r"|"
        r"\d{1,3}(?:,\d{2,3})+"
        r"|"
        r"\d+"
        r")"
    )

    # ---------------------------------------
    # Budget range
    # ---------------------------------------
    range_pattern = (
        rf"(?<!\w)"
        rf"({AMOUNT_PATTERN})"
        rf"\s*(?:and|to|-|–|—)\s*"
        rf"({AMOUNT_PATTERN})"
        rf"(?!\w)"
    )

    range_match = re.search(
        range_pattern,
        text,
        flags=re.IGNORECASE
    )

    if range_match:

        amount_a = _parse_amount(
            range_match.group(1)
        )

        amount_b = _parse_amount(
            range_match.group(2)
        )

        if (
            amount_a is not None
            and amount_b is not None
            and amount_a >= 1000
            and amount_b >= 1000
        ):
            prefs["budget_min"] = min(
                amount_a,
                amount_b
            )

            prefs["budget_max"] = max(
                amount_a,
                amount_b
            )

    else:

        # ---------------------------------------
        # Single upper limit
        #
        # under ₹30,000
        # below ₹30k
        # within 30000
        # max 30000
        # budget of ₹30,000
        # upto ₹30k
        # ---------------------------------------
        upper_bound_pattern = (
            rf"\b(?:under|below|within|"
            rf"max(?:imum)?|budget(?:\s+of)?|"
            rf"upto|up\s+to)"
            rf"\s*"
            rf"({AMOUNT_PATTERN})"
            rf"\b"
        )

        upper_match = re.search(
            upper_bound_pattern,
            text,
            flags=re.IGNORECASE
        )

        if upper_match:

            amount = _parse_amount(
                upper_match.group(1)
            )

            if (
                amount is not None
                and amount >= 1000
            ):
                prefs["budget_max"] = amount

        else:

            # ---------------------------------------
            # Standalone budget
            #
            # ₹30000
            # ₹30,000
            # 30k
            #
            # Avoid interpreting:
            # 5 days
            # 4 travelers
            # etc.
            # ---------------------------------------
            standalone_pattern = (
                rf"(?<!\w)"
                rf"({AMOUNT_PATTERN})"
                rf"(?!\w)"
            )

            standalone_matches = re.finditer(
                standalone_pattern,
                text,
                flags=re.IGNORECASE
            )

            for match in standalone_matches:

                raw_amount = match.group(1)

                amount = _parse_amount(
                    raw_amount
                )

                if amount is None:
                    continue

                # Budget should normally be >= 1000
                if amount < 1000:
                    continue

                # If it looks like a plain number,
                # don't accidentally treat a duration/
                # traveler count as budget.
                if (
                    not re.search(
                        r"[₹]|rs\.?|inr|k",
                        raw_amount,
                        flags=re.IGNORECASE
                    )
                    and amount < 10000
                ):
                    continue

                prefs["budget_max"] = amount
                break

    # =========================================================
    # 2. DURATION
    # =========================================================

    duration_match = re.search(
        r"\b(\d+)\s*[-\s]?(?:day|days)\b",
        text
    )

    if duration_match:

        prefs["duration_days"] = int(
            duration_match.group(1)
        )

    else:

        night_match = re.search(
            r"\b(\d+)\s*[-\s]?(?:night|nights)\b",
            text
        )

        if night_match:

            prefs["duration_days"] = (
                int(night_match.group(1)) + 1
            )

        elif re.search(
            r"\b(?:one|a)\s+week\b",
            text
        ):

            prefs["duration_days"] = 7

        elif re.search(
            r"\bweek\b",
            text
        ):

            prefs["duration_days"] = 7

    # =========================================================
    # 3. TRAVELERS
    # =========================================================

    travelers_match = re.search(
        r"\b(\d+)\s*"
        r"(?:people|travelers?|travellers?|"
        r"persons?|pax)\b",
        text
    )

    if travelers_match:

        prefs["travelers"] = int(
            travelers_match.group(1)
        )

    else:

        for_match = re.search(
            r"\bfor\s+(\d+)\b",
            text
        )

        if for_match:

            number = int(
                for_match.group(1)
            )

            if 1 <= number <= 20:
                prefs["travelers"] = number

        elif re.search(
            r"\bcouple\b|\bhoneymoon\b",
            text
        ):

            prefs["travelers"] = 2

        elif re.search(
            r"\bsolo\b",
            text
        ):

            prefs["travelers"] = 1

    # =========================================================
    # 4. START LOCATION
    # =========================================================
    # IMPORTANT:
    # Extract origin BEFORE destination.
    #
    # Example:
    # "Goa from Kochi"
    #
    # Kochi must NOT become destination Kerala.
    # =========================================================

    from_match = re.search(
        r"\bfrom\s+"
        r"([a-zA-Z][a-zA-Z\s]*?)"
        r"(?=\s+(?:to|for|with|under|below|within|"
        r"budget|in|on)\b|[,.;]|$)",
        text,
        flags=re.IGNORECASE
    )

    if from_match:

        candidate = (
            from_match.group(1)
            .strip()
        )

        candidate_lower = candidate.lower()

        # Match longest known origin first
        for origin in sorted(
            origin_set,
            key=len,
            reverse=True
        ):

            pattern = (
                rf"\b{re.escape(origin)}\b"
            )

            if re.search(
                pattern,
                candidate_lower,
                flags=re.IGNORECASE
            ):

                prefs["start_location"] = (
                    _normalise_city(origin)
                )

                break

        # If not found in known origins,
        # use the actual phrase after "from".
        if (
            prefs["start_location"] is None
            and len(candidate) >= 3
        ):

            prefs["start_location"] = (
                _normalise_city(candidate)
            )

    # =========================================================
    # 5. DESTINATION
    # =========================================================

    prefs["destination_region"] = (
        _find_destination_in_text(
            text,
            dest_dict,
            prefs["start_location"]
        )
    )
    if prefs["destination_region"]:
        known_destinations = {
            value.lower()
            for value in dest_dict.values()
        }
        prefs["destination_known"] = (
            prefs["destination_region"].lower()
            in known_destinations
        )

    # =========================================================
    # 6. PACE
    # =========================================================

    prefs["pace"] = _find_first_keyword_match(
        text,
        PACE_KEYWORDS
    )

    # =========================================================
    # 7. INTERESTS / THEMES
    # =========================================================

    matched_interests = []

    for theme, keywords in THEME_KEYWORDS.items():

        for keyword in keywords:

            if re.search(
                rf"\b{re.escape(keyword)}\b",
                text
            ):

                matched_interests.append(theme)
                break

    prefs["interests"] = matched_interests

    return prefs


# =============================================================
# TESTING
# =============================================================

if __name__ == "__main__":

    samples = [

        (
            "I want a 5 day trip to Goa from Kochi "
            "for 4 travelers, relaxed, "
            "budget between ₹20,000 and ₹30,000"
        ),

        (
            "Plan a 6 day Kerala trip from Bangalore "
            "for 2 people under ₹40,000"
        ),

        (
            "I want a 5 day Rajasthan trip from Delhi "
            "for 3 people within ₹30k"
        ),

        (
            "Plan a relaxed 7 day Kashmir trip from Kochi "
            "under ₹50,000"
        ),

        (
            "I want a 4 day trip to Alleppey from Kochi "
            "for 2 people under ₹25,000"
        ),

        (
            "I want a Goa trip under ₹30,000"
        ),

        (
            "I want a Goa trip with budget 30000"
        ),

        (
            "I want a Goa trip with budget ₹30k"
        ),

        (
            "I want a Goa trip between 20k and 30k"
        ),

        (
            "I want a Goa trip between ₹20,000–₹30,000"
        ),
    ]

    for prompt in samples:

        result = extract_preferences(prompt)

        print("=" * 70)
        print("PROMPT:")
        print(prompt)
        print()
        print("EXTRACTED:")
        print(result)
        print()