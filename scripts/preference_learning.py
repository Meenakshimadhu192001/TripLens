import os
import sqlite3
import json
from collections import Counter
from scripts.trip_history import get_trip_history
from scripts.user_profile import get_user_profile, init_user_tables

DB_PATH = os.path.join("database", "triplens.db")


def learn_from_prompt(user_id: str = "U001", preferences: dict = None):
    """Persist explicit preferences extracted from a user's search prompt."""
    init_user_tables()
    preferences = preferences or {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return None

    current = dict(row)
    preferred_destinations = json.loads(current["preferred_destinations_json"] or "[]")
    preferred_themes = json.loads(current["preferred_themes_json"] or "[]")
    preferred_pace = json.loads(current["preferred_pace_json"] or "[]")

    destination = preferences.get("destination_region")
    if destination and destination not in preferred_destinations:
        preferred_destinations.append(destination)

    for theme in preferences.get("interests") or []:
        theme = str(theme).strip().lower()
        if theme and theme not in preferred_themes:
            preferred_themes.append(theme)

    pace = preferences.get("pace")
    if pace and pace not in preferred_pace:
        preferred_pace.append(pace)

    budget_min = preferences.get("budget_min")
    budget_max = preferences.get("budget_max")
    known_min = current["preferred_budget_min"]
    known_max = current["preferred_budget_max"]
    budget_min = min(v for v in [known_min, budget_min] if v is not None) if any(v is not None for v in [known_min, budget_min]) else None
    budget_max = max(v for v in [known_max, budget_max] if v is not None) if any(v is not None for v in [known_max, budget_max]) else None

    duration = preferences.get("duration_days")
    known_duration_min = current["preferred_duration_min"]
    known_duration_max = current["preferred_duration_max"]
    duration_min = min(v for v in [known_duration_min, duration] if v is not None) if any(v is not None for v in [known_duration_min, duration]) else None
    duration_max = max(v for v in [known_duration_max, duration] if v is not None) if any(v is not None for v in [known_duration_max, duration]) else None

    home_location = preferences.get("start_location") or current["home_location"]
    conn.execute("""
        UPDATE user_profiles SET
            home_location = ?, preferred_destinations_json = ?, preferred_themes_json = ?,
            preferred_pace_json = ?, preferred_budget_min = ?, preferred_budget_max = ?,
            preferred_duration_min = ?, preferred_duration_max = ?, last_updated = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (
        home_location, json.dumps(preferred_destinations), json.dumps(preferred_themes),
        json.dumps(preferred_pace), budget_min, budget_max, duration_min, duration_max, user_id
    ))
    conn.commit()
    conn.close()
    return get_user_profile(user_id)

def refresh_user_preferences(user_id: str = "U001"):
    init_user_tables()
    history = get_trip_history(user_id)
    if not history:
        return

    visited_dests = []
    themes = []
    paces = []
    transports = []
    durations = []
    budgets = []
    disliked_items = []
    liked_items = []

    for trip in history:
        for d in trip["destinations"]:
            if d and d not in visited_dests:
                visited_dests.append(d)
        for t in trip["themes"]:
            if t:
                themes.append(t.lower())
        if trip["pace"]:
            paces.append(trip["pace"])
        if trip["transport"]:
            transports.append(trip["transport"])
        if trip["duration_days"]:
            durations.append(trip["duration_days"])
        if trip["budget_spent_inr"]:
            budgets.append(trip["budget_spent_inr"])
        for item in trip.get("liked", []):
            if item:
                liked_items.append(item.lower())
        for item in trip.get("disliked", []):
            if item:
                disliked_items.append(item.lower())

    theme_counts = Counter(themes + liked_items)
    top_themes = [item for item, _ in theme_counts.most_common(5)]

    pace_counts = Counter(paces)
    top_paces = [item for item, _ in pace_counts.most_common(3)]

    transport_counts = Counter(transports)
    top_transports = [item for item, _ in transport_counts.most_common(3)]

    min_budget = min(budgets) if budgets else None
    max_budget = max(budgets) if budgets else None

    min_duration = min(durations) if durations else None
    max_duration = max(durations) if durations else None

    disliked_counts = Counter(disliked_items)
    avoided = [item for item, count in disliked_counts.items() if count >= 1]

    total_trips = len(history)
    confidence = {}
    for t in top_themes:
        count = theme_counts[t]
        confidence[t] = round(min(0.95, 0.3 + (count / max(total_trips, 1)) * 0.6), 2)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_profiles SET
            visited_destinations_json = ?,
            preferred_themes_json = ?,
            preferred_pace_json = ?,
            preferred_transport_json = ?,
            preferred_budget_min = ?,
            preferred_budget_max = ?,
            preferred_duration_min = ?,
            preferred_duration_max = ?,
            avoided_preferences_json = ?,
            confidence_json = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (
        json.dumps(visited_dests),
        json.dumps(top_themes),
        json.dumps(top_paces),
        json.dumps(top_transports),
        min_budget,
        max_budget,
        min_duration,
        max_duration,
        json.dumps(avoided),
        json.dumps(confidence),
        user_id
    ))
    conn.commit()
    conn.close()
