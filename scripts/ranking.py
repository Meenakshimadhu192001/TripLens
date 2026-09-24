"""
TripLens - Hybrid Ranking Engine + Explainability

Ranks travel packages using:
- Budget
- Destination
- Duration
- Interests
- Pace
- Semantic similarity

Explicit destination and budget constraints are enforced.
"""

import re
import os
import sys

# Allow direct execution:
# python Scripts/ranking.py
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.ranking_weights import RANKING_WEIGHTS


def score_budget_fit(price, budget_min, budget_max):
    """Score package price against user budget."""

    if price is None:
        return 0.0, {
            "text": "Package price is not available",
            "positive": False,
        }

    price = float(price)

    if budget_min is None and budget_max is None:
        return 0.7, None

    if budget_min is not None and budget_max is not None:

        if budget_min <= price <= budget_max:
            return 1.0, {
                "text": (
                    f"Within your budget range "
                    f"(₹{int(price):,} fits "
                    f"₹{int(budget_min):,}–₹{int(budget_max):,})"
                ),
                "positive": True,
            }

        if price < budget_min:
            difference = budget_min - price

            return 0.0, {
                "text": (
                    f"₹{int(difference):,} below your "
                    f"minimum budget of ₹{int(budget_min):,}"
                ),
                "positive": False,
            }

        difference = price - budget_max

        return 0.0, {
            "text": (
                f"₹{int(difference):,} above your "
                f"maximum budget of ₹{int(budget_max):,}"
            ),
            "positive": False,
        }

    if budget_max is not None:

        if price <= budget_max:
            return 1.0, {
                "text": (
                    f"Within your maximum budget "
                    f"(₹{int(price):,} ≤ ₹{int(budget_max):,})"
                ),
                "positive": True,
            }

        return 0.0, {
            "text": (
                f"₹{int(price - budget_max):,} above your "
                f"maximum budget of ₹{int(budget_max):,}"
            ),
            "positive": False,
        }

    if budget_min is not None:

        if price >= budget_min:
            return 1.0, {
                "text": (
                    f"Meets your minimum budget "
                    f"(₹{int(price):,} ≥ ₹{int(budget_min):,})"
                ),
                "positive": True,
            }

        return 0.0, {
            "text": (
                f"₹{int(budget_min - price):,} below your "
                f"minimum budget of ₹{int(budget_min):,}"
            ),
            "positive": False,
        }

    return 0.7, None


def score_destination_fit(
    destinations_str,
    start_location_actual,
    destination_region,
    start_location_pref,
    package_name=""
):
    """Score destination compatibility."""

    if not destination_region:
        return 0.7, None

    dest_pref = destination_region.lower().strip()

    searchable = (
        f"{destinations_str or ''} "
        f"{package_name or ''}"
    ).lower()

    tokens = [
        token
        for token in re.split(
            r"[,/;&\-\s]+",
            dest_pref
        )
        if len(token) >= 3
        and token not in {
            "pradesh",
            "island",
            "islands",
            "north",
            "south",
            "east",
            "west",
        }
    ]

    if not tokens:
        tokens = [dest_pref]

    destination_matches = (
        dest_pref in searchable
        or any(
            re.search(
                rf"\b{re.escape(token)}\b",
                searchable
            )
            for token in tokens
        )
    )

    if destination_matches:

        destination_score = 1.0

        reason = {
            "text": (
                f"Destination matches your "
                f"requested {destination_region}"
            ),
            "positive": True,
        }

    else:

        destination_score = 0.0

        reason = {
            "text": (
                f"Destinations "
                f"({destinations_str}) don't match "
                f"your requested {destination_region}"
            ),
            "positive": False,
        }

    # Check origin separately.
    if start_location_pref and start_location_actual:

        preferred_start = (
            start_location_pref.lower().strip()
        )

        actual_start = (
            str(start_location_actual)
            .lower()
            .strip()
        )

        if (
            preferred_start not in actual_start
            and actual_start not in preferred_start
        ):

            if destination_score == 1.0:
                return 0.8, {
                    "text": (
                        f"Starts from "
                        f"{start_location_actual}, "
                        f"not your requested "
                        f"{start_location_pref}"
                    ),
                    "positive": False,
                }

            return 0.0, {
                "text": (
                    f"Starts from "
                    f"{start_location_actual}, "
                    f"not your requested "
                    f"{start_location_pref}"
                ),
                "positive": False,
            }

    return destination_score, reason


def score_duration_fit(
    duration_days_actual,
    duration_days_pref
):
    """Score duration compatibility."""

    if (
        not duration_days_pref
        or duration_days_actual is None
    ):
        return 0.7, None

    diff = abs(
        int(duration_days_actual)
        - int(duration_days_pref)
    )

    if diff == 0:
        return 1.0, {
            "text": (
                f"Duration matches your requested "
                f"{duration_days_pref} days exactly"
            ),
            "positive": True,
        }

    if diff == 1:
        return 0.7, {
            "text": (
                f"{int(duration_days_actual)} days, "
                f"close to your requested "
                f"{duration_days_pref} days"
            ),
            "positive": True,
        }

    return 0.3, {
        "text": (
            f"{int(duration_days_actual)} days instead of "
            f"your requested "
            f"{duration_days_pref} days"
        ),
        "positive": False,
    }


def score_interest_fit(theme_clean, interests_pref):
    """Score interest compatibility."""

    if not interests_pref:
        return 0.6, None

    theme_text = str(
        theme_clean or ""
    ).lower()

    matched = [
        interest
        for interest in interests_pref
        if interest.lower() in theme_text
    ]

    if matched:
        return 1.0, {
            "text": (
                f"Matches your interest in "
                f"{', '.join(matched)}"
            ),
            "positive": True,
        }

    return 0.3, {
        "text": (
            f"Theme ({theme_clean}) doesn't clearly "
            f"match your interests "
            f"({', '.join(interests_pref)})"
        ),
        "positive": False,
    }


def score_pace_fit(
    itinerary_pace_inferred,
    pace_pref
):
    """Score itinerary pace compatibility."""

    if not pace_pref:
        return 0.7, None

    if (
        str(itinerary_pace_inferred).lower()
        == str(pace_pref).lower()
    ):
        return 1.0, {
            "text": (
                f"Pace matches your preferred "
                f"{pace_pref} style"
            ),
            "positive": True,
        }

    return 0.5, {
        "text": (
            f"Pace is {itinerary_pace_inferred}, "
            f"you preferred {pace_pref}"
        ),
        "positive": False,
    }


def rank_candidates(candidates, prefs):
    """Rank candidates after applying hard constraints."""

    ranked = []

    destination_required = (
        prefs.get("destination_region") or ""
    ).strip()

    budget_min = prefs.get("budget_min")
    budget_max = prefs.get("budget_max")

    for pkg in candidates:

        price = pkg.get("price")

        budget_score, budget_reason = score_budget_fit(
            price,
            budget_min,
            budget_max
        )

        destination_score, destination_reason = (
            score_destination_fit(
                pkg.get("destinations"),
                pkg.get("start_location"),
                destination_required,
                prefs.get("start_location"),
                pkg.get("package_name", "")
            )
        )

        duration_score, duration_reason = score_duration_fit(
            pkg.get("duration_days"),
            prefs.get("duration_days")
        )

        interest_score, interest_reason = score_interest_fit(
            pkg.get("theme_clean"),
            prefs.get("interests")
        )

        pace_score, pace_reason = score_pace_fit(
            pkg.get("itinerary_pace_inferred"),
            prefs.get("pace")
        )

        semantic_score = float(
            pkg.get("semantic_similarity", 0.0)
        )

        # --------------------------------------------------
        # HARD DESTINATION FILTER
        # --------------------------------------------------

        if destination_required:
            if destination_score != 1.0:
                continue

        # --------------------------------------------------
        # HARD BUDGET FILTER
        # --------------------------------------------------

        if budget_min is not None:

            if price is None:
                continue

            if float(price) < float(budget_min):
                continue

        if budget_max is not None:

            if price is None:
                continue

            if float(price) > float(budget_max):
                continue

        # --------------------------------------------------
        # WEIGHTED SCORE
        # --------------------------------------------------

        weights = RANKING_WEIGHTS

        raw_score = (
            weights["budget_fit"] * budget_score
            + weights["destination_match"] * destination_score
            + weights["duration_fit"] * duration_score
            + weights["interest_match"] * interest_score
            + weights["pace_match"] * pace_score
            + weights["semantic_similarity"] * semantic_score
        )

        reasons = [
            reason
            for reason in (
                destination_reason,
                budget_reason,
                interest_reason,
                pace_reason,
                duration_reason
            )
            if reason is not None
        ]

        ranked.append(
            {
                "package_id": pkg.get("package_id"),
                "package_name": pkg.get("package_name"),
                "agency_name": pkg.get("agency_name"),
                "source_url_or_doc": pkg.get(
                    "source_url_or_doc"
                ),
                "destinations": pkg.get(
                    "destinations"
                ),
                "start_location": pkg.get(
                    "start_location"
                ),
                "theme": pkg.get("theme_clean"),
                "pace": pkg.get(
                    "itinerary_pace_inferred"
                ),
                "price": pkg.get("price"),
                "duration_days": pkg.get(
                    "duration_days"
                ),
                "fit_score": round(
                    raw_score * 100,
                    1
                ),
                "score_breakdown": {
                    "budget_fit": round(
                        budget_score, 2
                    ),
                    "destination_match": round(
                        destination_score, 2
                    ),
                    "duration_fit": round(
                        duration_score, 2
                    ),
                    "interest_match": round(
                        interest_score, 2
                    ),
                    "pace_match": round(
                        pace_score, 2
                    ),
                    "semantic_similarity": round(
                        semantic_score, 2
                    ),
                },
                "reasons": reasons,
            }
        )

    ranked.sort(
        key=lambda item: item["fit_score"],
        reverse=True
    )

    return ranked


if __name__ == "__main__":

    from scripts.preference_extraction import (
        extract_preferences
    )

    from scripts.retrieval import (
        get_candidates
    )

    sample = (
        "I want a relaxed 5-day Kerala trip "
        "from Kochi for 2 people under ₹30,000 "
        "with beaches, nature and sightseeing."
    )

    print("\nPROMPT:")
    print(sample)

    prefs = extract_preferences(sample)

    print("\nPREFERENCES:")
    print(prefs)

    candidates = get_candidates(
        prefs,
        sample,
        top_k=10
    )

    print("\nRETRIEVED CANDIDATES:")

    for candidate in candidates:

        print(
            candidate.get("package_id"),
            "|",
            candidate.get("package_name"),
            "| dest:",
            candidate.get("destinations"),
            "| price:",
            candidate.get("price")
        )

    ranked = rank_candidates(
        candidates,
        prefs
    )

    print("\nFINAL RANKED RESULTS:")

    if not ranked:

        print(
            "No packages satisfy the "
            "requested constraints."
        )

    else:

        for result in ranked:

            print(
                f"\n{result['package_id']} — "
                f"{result['package_name']} "
                f"| Fit: {result['fit_score']}% "
                f"| ₹{result['price']}"
            )

            for reason in result["reasons"]:

                mark = (
                    "✓"
                    if reason["positive"]
                    else "⚠"
                )

                print(
                    f" {mark} "
                    f"{reason['text']}"
                )
