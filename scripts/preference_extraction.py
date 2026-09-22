"""
TripLens - NLP Preference Extraction
Deterministic first pass (regex-based). Never invents values it can't find —
missing fields stay None so the UI can ask the user to confirm/edit, per the
project's "never invent information" rule.
"""

import re


REGION_KEYWORDS = {
    "Kerala": [
        "kerala", "munnar", "alleppey", "wayanad",
        "kovalam", "thekkady", "kochi"
    ],
    "Himachal Pradesh": [
        "himachal", "shimla", "manali", "kasol",
        "manikaran", "dalhousie", "dharamshala"
    ],
    "Goa": ["goa"],
    "Kashmir": ["kashmir", "srinagar", "gulmarg", "pahalgam"],
    "Andaman": ["andaman", "port blair", "havelock"],
    "Sikkim": ["sikkim", "gangtok"],
    "North East": ["north east", "shillong", "meghalaya", "assam"],
}


THEME_KEYWORDS = {
    "nature": [
        "nature", "greenery", "waterfalls",
        "hills", "scenic", "forest", "wildlife"
    ],
    "beach": ["beach", "coast", "island"],
    "backwaters": ["backwater", "houseboat"],
    "adventure": [
        "adventure", "trek", "rafting", "paragliding"
    ],
    "heritage": [
        "heritage", "temple", "fort", "culture", "historic"
    ],
    "pilgrimage": [
        "pilgrimage", "spiritual", "temple visit"
    ],
    "hill-station": [
        "hill station", "mountains", "snow", "valley"
    ],
    "honeymoon/romance": [
        "honeymoon", "romantic", "couple"
    ],
    "family": ["family", "kids"],
}


PACE_KEYWORDS = {
    "Relaxed": [
        "relaxed", "leisure", "slow",
        "peaceful", "unrushed"
    ],
    "Packed": [
        "active", "packed", "fast-paced",
        "full circuit", "express"
    ],
}


def _find_first_keyword_match(text, keyword_map):
    for label, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text:
                return label
    return None


def extract_preferences(prompt_text: str) -> dict:
    text = prompt_text.lower()

    prefs = {
        "destination_region": None,
        "start_location": None,
        "duration_days": None,
        "budget_min": None,
        "budget_max": None,
        "travelers": None,
        "pace": None,
        "interests": [],
    }

    # --------------------------------------------------
    # Budget
    # Supports:
    # ₹30,000
    # 30000
    # 30k
    # between 20000 and 30000
    # --------------------------------------------------

    amount_pattern = r"(\d[\d,]*(?:\.\d+)?k?)"

    range_match = re.search(
        rf"(?:between|from)?\s*"
        rf"(?:₹|rs\.?)?\s*{amount_pattern}"
        rf"\s*(?:and|to|-)\s*"
        rf"(?:₹|rs\.?)?\s*{amount_pattern}",
        text,
    )

    if range_match:
        prefs["budget_min"] = _parse_amount(range_match.group(1))
        prefs["budget_max"] = _parse_amount(range_match.group(2))

    else:
        single_match = re.search(
            rf"(?:under|below|budget|within|max)"
            rf"\s*(?:of)?\s*"
            rf"(?:₹|rs\.?)?\s*{amount_pattern}",
            text,
        )

        if single_match:
            prefs["budget_max"] = _parse_amount(
                single_match.group(1)
            )

    # --------------------------------------------------
    # Duration
    # --------------------------------------------------

    duration_match = re.search(
        r"(\d+)\s*-?\s*day",
        text
    )

    if duration_match:
        prefs["duration_days"] = int(
            duration_match.group(1)
        )

    elif "week" in text:
        prefs["duration_days"] = 7

    # --------------------------------------------------
    # Travelers
    # --------------------------------------------------

    travelers_match = re.search(
        r"(\d+)\s*(?:people|travelers|travellers|persons|pax)",
        text
    )

    if travelers_match:
        prefs["travelers"] = int(
            travelers_match.group(1)
        )

    elif "couple" in text or "2 people" in text:
        prefs["travelers"] = 2

    # --------------------------------------------------
    # Destination
    # --------------------------------------------------

    prefs["destination_region"] = _find_first_keyword_match(
        text,
        REGION_KEYWORDS
    )

    # --------------------------------------------------
    # Start location
    # --------------------------------------------------

    for city in [
        "delhi",
        "kochi",
        "chandigarh",
        "bangalore",
        "bengaluru",
        "mumbai",
        "chennai",
        "kolkata",
        "hyderabad",
    ]:
        if city in text:
            prefs["start_location"] = city.title()
            break

    # --------------------------------------------------
    # Pace
    # --------------------------------------------------

    prefs["pace"] = (
        _find_first_keyword_match(
            text,
            PACE_KEYWORDS
        )
        or "Moderate"
    )

    # --------------------------------------------------
    # Interests
    # --------------------------------------------------

    matched_interests = []

    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched_interests.append(theme)

    prefs["interests"] = matched_interests

    return prefs


def _parse_amount(raw: str) -> int:
    raw = raw.strip().lower()

    if raw.endswith("k"):
        return int(float(raw[:-1]) * 1000)

    return int(raw.replace(",", ""))


if __name__ == "__main__":
    sample = (
        "I want a relaxed 5-day Kerala trip from Kochi "
        "for 2 people under ₹30,000 with beaches, "
        "nature and sightseeing."
    )

    print(extract_preferences(sample))