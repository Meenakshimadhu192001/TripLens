"""
TripLens - Proactive Next Trip Recommendation Engine
Supports modes:
1. 'preferences': Balanced recommendation using learned preferences
2. 'something_new': High novelty preference / exploration
3. 'similar_last': Uses the latest completed trip as the primary reference template
"""
import sqlite3
import os
import json
import uuid
from scripts.user_profile import get_user_profile
from scripts.trip_history import get_trip_history
from scripts.retrieval import get_candidates
from scripts.ranking import (
    score_budget_fit, score_destination_fit, score_duration_fit,
    score_interest_fit, score_pace_fit
)
from scripts.novelty import compute_novelty_score
from scripts.recommendation_explanations import generate_recommendation_explanation

DB_PATH = os.path.join("database", "triplens.db")

def get_next_trip_suggestions(user_id: str = "U001", mode: str = "preferences", top_k: int = 6) -> dict:
    profile = get_user_profile(user_id)
    history = get_trip_history(user_id)

    # Cold Start Check
    has_learned_preferences = profile and any([
        profile.get("preferred_themes"),
        profile.get("preferred_destinations"),
        profile.get("preferred_budget_range", {}).get("min") is not None,
        profile.get("preferred_duration_range", {}).get("min_days") is not None,
        profile.get("preferred_pace"),
    ])
    if not profile or not profile["personalization_enabled"] or (not history and not has_learned_preferences):
        # Fallback to cold-start general recommendations
        return _get_cold_start_suggestions(top_k)

    last_trip = history[0] if history else None

    # Construct search query prompt from historical preferences
    preferred_themes = profile.get("preferred_themes", [])
    prompt_parts = []
    if mode == "similar_last" and last_trip:
        prompt_parts.append(f"Trip similar to {', '.join(last_trip['destinations'])} with {' '.join(last_trip['themes'])}")
    elif mode == "something_new":
        prompt_parts.append(f"New unseen destination with {' '.join(preferred_themes)}")
    else:
        prompt_parts.append(f"Trip matching {' '.join(preferred_themes)} nature scenic relaxed getaway")

    search_prompt = " ".join(prompt_parts)

    prefs = {
        "destination_region": None,
        "start_location": profile.get("home_location"),
        "duration_days": (profile["preferred_duration_range"]["min_days"] + profile["preferred_duration_range"]["max_days"]) // 2 if profile["preferred_duration_range"]["min_days"] else 5,
        "budget_min": profile["preferred_budget_range"]["min"],
        "budget_max": profile["preferred_budget_range"]["max"],
        "pace": profile["preferred_pace"][0] if profile["preferred_pace"] else "Moderate",
        "interests": profile.get("preferred_themes", [])
    }

    candidates = get_candidates(prefs, search_prompt, top_k=max(top_k * 3, 20))
    visited_dests = profile.get("visited_destinations", [])
    avoided = [a.lower() for a in profile.get("avoided_preferences", [])]

    scored = []
    for pkg in candidates:
        budget_score, budget_reason = score_budget_fit(pkg.get("price"), prefs.get("budget_min"), prefs.get("budget_max"))
        duration_score, duration_reason = score_duration_fit(pkg.get("duration_days"), prefs.get("duration_days"))
        interest_score, interest_reason = score_interest_fit(pkg.get("theme_clean"), prefs.get("interests"))
        pace_score, pace_reason = score_pace_fit(pkg.get("itinerary_pace_inferred"), prefs.get("pace"))
        semantic_score = pkg.get("semantic_similarity", 0.0)
        novelty_score, novelty_reason = compute_novelty_score(pkg.get("destinations", ""), visited_dests)

        # Avoidance penalty
        avoid_penalty = 0.0
        pkg_desc = f"{pkg.get('package_name')} {pkg.get('itinerary_pace_inferred')} {pkg.get('theme_clean')}".lower()
        for avoid_term in avoided:
            if avoid_term in pkg_desc:
                avoid_penalty += 0.25

        # Mode-based weight adjustments
        if mode == "something_new":
            w_novelty = 0.30
            w_pref = 0.20
        elif mode == "similar_last":
            w_novelty = 0.05
            w_pref = 0.35
        else:
            w_novelty = 0.15
            w_pref = 0.25

        final_score = (
            w_pref * interest_score +
            0.15 * budget_score +
            0.10 * duration_score +
            0.10 * pace_score +
            0.10 * semantic_score +
            w_novelty * novelty_score +
            0.10 * (pkg.get("data_completeness_score", 80) / 100)
            - avoid_penalty
        )
        final_score = max(0.0, min(1.0, final_score))

        reasons = [r for r in [interest_reason, budget_reason, duration_reason, pace_reason, novelty_reason] if r]
        explanation = generate_recommendation_explanation(pkg, profile, reasons)

        scored.append({
            "package_id": pkg["package_id"],
            "package_name": pkg["package_name"],
            "agency_name": pkg.get("agency_name"),
            "destinations": pkg.get("destinations"),
            "start_location": pkg.get("start_location"),
            "duration_days": pkg.get("duration_days"),
            "price": pkg.get("price"),
            "theme": pkg.get("theme_clean"),
            "fit_score": round(final_score * 100, 1),
            "novelty_score": round(novelty_score * 100, 1),
            "reasons": reasons,
            "explanation": explanation
        })

    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    results = scored[:top_k]

    # Record recommendations in DB
    _log_recommendations(user_id, results, mode)

    return {
        "mode": mode,
        "is_cold_start": False,
        "user_id": user_id,
        "results": results
    }

def _get_cold_start_suggestions(top_k: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM packages_enriched ORDER BY data_completeness_score DESC LIMIT ?", (top_k,)).fetchall()
    conn.close()

    results = []
    for r in rows:
        pkg = dict(r)
        results.append({
            "package_id": pkg["package_id"],
            "package_name": pkg["package_name"],
            "agency_name": pkg.get("agency_name"),
            "destinations": pkg.get("destinations"),
            "start_location": pkg.get("start_location"),
            "duration_days": pkg.get("duration_days"),
            "price": pkg.get("price"),
            "theme": pkg.get("theme_clean"),
            "fit_score": round(pkg.get("data_completeness_score", 80), 1),
            "novelty_score": 100.0,
            "reasons": [{"text": "High data quality & popular package", "positive": True}],
            "explanation": {
                "title": f"Featured Package: {pkg.get('package_name')}",
                "matched_reasons": ["Popular package with complete itinerary details"],
                "potential_concerns": []
            }
        })

    return {
        "mode": "cold_start",
        "is_cold_start": True,
        "user_id": "U001",
        "results": results
    }

def _log_recommendations(user_id: str, results: list, mode: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in results:
        rec_id = f"REC_{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO recommendation_history (recommendation_id, user_id, package_id, recommendation_type, reason_codes_json)
            VALUES (?, ?, ?, ?, ?)
        """, (rec_id, user_id, item["package_id"], mode, json.dumps([r["text"] for r in item.get("reasons", [])])))
    conn.commit()
    conn.close()
