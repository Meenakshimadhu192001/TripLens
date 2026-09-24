"""
TripLens API - Main Entrypoint
Chains preference extraction -> semantic retrieval -> hybrid ranking
-> explainability into one /search endpoint for the existing frontend.
"""
from pathlib import Path

import re
import sqlite3

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from scripts.preference_extraction import extract_preferences
from scripts.retrieval import get_candidates
from scripts.ranking import rank_candidates

app = FastAPI(title="TripLens API")
PROJECT_ROOT = Path(__file__).resolve().parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual frontend origin before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    prompt: str
    top_k: int = 10


class PromptLearningRequest(BaseModel):
    user_id: str = "U001"
    prompt: str
    destination_region: str | None = None
    start_location: str | None = None
    duration_days: int | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    pace: str | None = None
    interests: list[str] | None = None


class PreferenceOverride(BaseModel):
    prompt: str
    destination_region: str | None = None
    start_location: str | None = None
    duration_days: int | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    travelers: int | None = None
    pace: str | None = None
    interests: list[str] | None = None
    top_k: int = 10


class ItineraryDayInput(BaseModel):
    day_number: int
    stops: str
    activities: str
    activity_type: str
    distance_km: float = 0
    transit_hours: float = 0
    stops_requiring_separate_drives: int = 0
    meals_included_today: str


class AccommodationInput(BaseModel):
    destination: str
    accommodation_category: str
    hotel_name: str
    hotel_guaranteed: str


class PackageInput(BaseModel):
    package_id: str
    agency_name: str
    package_name: str
    destinations: str
    start_location: str
    duration_days: int
    duration_nights: int
    price: float
    list_price: float
    transport_type: str
    theme: str
    itinerary_pace: str
    agency_contact: str
    itinerary: list[ItineraryDayInput]
    accommodation: list[AccommodationInput]
    inclusions: list[str]
    exclusions: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend():
    """Serve the single-page client from the same origin as the API."""
    return FileResponse(PROJECT_ROOT / "index.html")


app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")


@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse(PROJECT_ROOT / "styles.css", media_type="text/css")


@app.get("/design-system.css", include_in_schema=False)
def design_system():
    return FileResponse(PROJECT_ROOT / "design-system.css", media_type="text/css")


@app.get("/data.js", include_in_schema=False)
def data_script():
    return FileResponse(PROJECT_ROOT / "data.js", media_type="application/javascript")


@app.get("/app.js", include_in_schema=False)
def app_script():
    return FileResponse(PROJECT_ROOT / "app.js", media_type="application/javascript")


@app.get("/manage", include_in_schema=False)
def manage_packages_page():
    return FileResponse(PROJECT_ROOT / "manage.html")


@app.get("/manage.js", include_in_schema=False)
def manage_script():
    return FileResponse(PROJECT_ROOT / "manage.js", media_type="application/javascript")


@app.get("/api/data-quality")
def data_quality_report():
    """Expose source-data gaps explicitly; values are never fabricated."""
    from scripts.data_access import get_db_connection
    conn = get_db_connection()
    required = ["package_name", "destinations", "start_location", "duration_days", "duration_nights", "price", "list_price", "transport_type", "theme", "itinerary_pace", "agency_contact"]
    missing = {
        field: conn.execute(f"SELECT COUNT(*) FROM packages WHERE {field} IS NULL OR TRIM(CAST({field} AS TEXT)) = ''").fetchone()[0]
        for field in required
    }
    relation_gaps = {
        "packages_without_itinerary": conn.execute("SELECT COUNT(*) FROM packages p WHERE NOT EXISTS (SELECT 1 FROM itinerary_days d WHERE d.package_id = p.package_id)").fetchone()[0],
        "packages_without_accommodation": conn.execute("SELECT COUNT(*) FROM packages p WHERE NOT EXISTS (SELECT 1 FROM accommodation a WHERE a.package_id = p.package_id)").fetchone()[0],
        "packages_without_inclusions": conn.execute("SELECT COUNT(*) FROM packages p WHERE NOT EXISTS (SELECT 1 FROM inclusions i WHERE i.package_id = p.package_id)").fetchone()[0],
        "packages_without_exclusions": conn.execute("SELECT COUNT(*) FROM packages p WHERE NOT EXISTS (SELECT 1 FROM exclusions e WHERE e.package_id = p.package_id)").fetchone()[0],
        "itinerary_duration_mismatches": conn.execute("SELECT COUNT(*) FROM (SELECT p.package_id FROM packages p LEFT JOIN itinerary_days d ON d.package_id=p.package_id GROUP BY p.package_id, p.duration_days HAVING COUNT(d.id) != CAST(p.duration_days AS INTEGER))").fetchone()[0],
    }
    total = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    conn.close()
    return {"packages": total, "missing_core_fields": missing, "relation_gaps": relation_gaps}


@app.get("/api/destinations")
def get_destinations():
    """Return all destination names dynamically discovered from the database."""
    from scripts.preference_extraction import load_db_destinations_and_origins
    dest_dict, _ = load_db_destinations_and_origins()
    unique_dests = sorted(set(dest_dict.values()))
    return {"destinations": unique_dests}


@app.post("/api/packages", status_code=201)
def create_package(payload: PackageInput, authorization: str | None = Header(default=None)):
    """Create one complete package and all four checklist sections atomically."""
    from scripts.auth_service import verify_session_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Packager login required.")
    session = verify_session_token(authorization[7:].strip())
    if not session or session.get("role") not in {"packager", "admin"}:
        raise HTTPException(status_code=403, detail="Only packagers or admins can save packages.")

    package_id = payload.package_id.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{3,40}", package_id):
        raise HTTPException(status_code=422, detail="Package ID must contain only letters, numbers, _ or -.")
    if payload.duration_days < 1 or payload.duration_nights < 0 or payload.price < 0 or payload.list_price < 0:
        raise HTTPException(status_code=422, detail="Duration and prices must be valid non-negative values.")
    if payload.duration_nights != max(payload.duration_days - 1, 0):
        raise HTTPException(status_code=422, detail=f"Duration nights must equal duration days - 1 (for {payload.duration_days} days, nights must be {max(payload.duration_days - 1, 0)}).")
    if payload.list_price < payload.price:
        raise HTTPException(status_code=422, detail="List price must be greater than or equal to price.")
    if len(payload.itinerary) != payload.duration_days:
        raise HTTPException(status_code=422, detail="Add exactly one itinerary row for every duration day.")
    if sorted(day.day_number for day in payload.itinerary) != list(range(1, payload.duration_days + 1)):
        raise HTTPException(status_code=422, detail="Itinerary day numbers must run consecutively from 1 to duration_days.")
    if not payload.accommodation or not payload.inclusions or not payload.exclusions:
        raise HTTPException(status_code=422, detail="At least one stay, inclusion, and exclusion is required.")
    if any(stay.hotel_guaranteed not in {"Yes", "No"} for stay in payload.accommodation):
        raise HTTPException(status_code=422, detail="hotel_guaranteed must be Yes or No.")

    from scripts.data_access import get_db_connection
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""INSERT INTO packages (package_id, agency_name, package_name, destinations, start_location, duration_days, duration_nights, price, list_price, transport_type, theme, itinerary_pace, agency_contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (package_id, payload.agency_name.strip(), payload.package_name.strip(), payload.destinations.strip(), payload.start_location.strip(), payload.duration_days, payload.duration_nights, payload.price, payload.list_price, payload.transport_type.strip(), payload.theme.strip(), payload.itinerary_pace.strip(), payload.agency_contact.strip()))
        conn.executemany("""INSERT INTO itinerary_days (package_id, day_number, stops, activities, activity_type, distance_km, transit_hours, stops_requiring_separate_drives, meals_included_today)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [(package_id, day.day_number, day.stops.strip(), day.activities.strip(), day.activity_type.strip(), day.distance_km, day.transit_hours, day.stops_requiring_separate_drives, day.meals_included_today.strip()) for day in payload.itinerary])
        conn.executemany("INSERT INTO accommodation (package_id, destination, accommodation_category, hotel_name, hotel_guaranteed) VALUES (?, ?, ?, ?, ?)", [(package_id, stay.destination.strip(), stay.accommodation_category.strip(), stay.hotel_name.strip(), stay.hotel_guaranteed) for stay in payload.accommodation])
        conn.executemany("INSERT INTO inclusions (package_id, inclusion_item) VALUES (?, ?)", [(package_id, item.strip()) for item in payload.inclusions if item.strip()])
        conn.executemany("INSERT INTO exclusions (package_id, exclusion_item) VALUES (?, ?)", [(package_id, item.strip()) for item in payload.exclusions if item.strip()])
        conn.commit()
    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Package could not be saved: {error}") from error
    finally:
        conn.close()

    # Keep semantic search in sync with packages created from the manager.
    try:
        from scripts.chroma_sync import sync_package_to_chroma
        day_summary = "; ".join(
            f"Day {day.day_number} ({day.stops}): {day.activities}"
            for day in payload.itinerary
        )
        accommodation_summary = ", ".join(
            f"{stay.destination} ({stay.accommodation_category})"
            for stay in payload.accommodation
        )
        sync_package_to_chroma({
            "package_id": package_id,
            "package_name": payload.package_name,
            "start_location": payload.start_location,
            "duration_days": payload.duration_days,
            "price": payload.price,
            "total_transit_hours": sum(day.transit_hours for day in payload.itinerary),
            "canonical_text": (
                f"Package: {payload.package_name} by {payload.agency_name}. "
                f"Start location: {payload.start_location}. Destinations: {payload.destinations}. "
                f"Duration: {payload.duration_days} days. Pace: {payload.itinerary_pace}. "
                f"Price: Rs {payload.price}. Daily itinerary: {day_summary}. "
                f"Accommodations: {accommodation_summary}."
            ),
        })
    except Exception as error:
        # Database persistence has already succeeded; search sync can be retried later.
        print(f"[CHROMA] Package {package_id} saved but index sync failed: {error}")

    excel_workbooks = []
    try:
        from scripts.excel_sync import sync_package_to_excel
        excel_workbooks = sync_package_to_excel(payload)
    except Exception as error:
        # Keep the database save successful if a workbook is locked or unavailable.
        print(f"[EXCEL] Package {package_id} saved but workbook sync failed: {error}")

    return {
        "package_id": package_id,
        "message": "Complete package saved.",
        "excel_updated": bool(excel_workbooks),
        "excel_workbooks": excel_workbooks,
    }


@app.post("/extract-preferences")
def extract_preferences_endpoint(req: SearchRequest):
    """Step 1: parse the natural-language prompt into structured preferences
    for the user to review/edit before we search."""
    prefs = extract_preferences(req.prompt)
    return {"prompt": req.prompt, "preferences": prefs}


@app.post("/search")
def search_endpoint(req: PreferenceOverride):
    """Step 2: retrieve + rank packages, using the (possibly user-edited)
    preferences rather than re-parsing the prompt from scratch."""
    prefs = {
        "destination_region": req.destination_region,
        "start_location": req.start_location,
        "duration_days": req.duration_days,
        "budget_min": req.budget_min,
        "budget_max": req.budget_max,
        "travelers": req.travelers,
        "pace": req.pace,
        "interests": req.interests or [],
    }

    candidates = get_candidates(prefs, req.prompt, top_k=max(req.top_k * 2, 15))
    if not candidates:
        return {"results": [], "message": "No suitable packages found."}

    ranked = rank_candidates(candidates, prefs)
    return {"results": ranked[: req.top_k]}


@app.post("/api/learn-prompt")
def learn_prompt_endpoint(req: PromptLearningRequest):
    """Store explicit preferences from a prompt for future recommendations."""
    from scripts.preference_learning import learn_from_prompt
    profile = learn_from_prompt(req.user_id, req.dict())
    return {"status": "learned", "user_id": req.user_id, "profile": profile}


@app.get("/package/{package_id}")
def get_package_detail(package_id: str):
    """Full detail for one package: overview, itinerary, inclusions/exclusions,
    accommodation. Reviews/trust are explicitly marked unavailable."""
    from scripts.data_access import get_db_connection, get_itinerary_metrics
    import sqlite3

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM packages_enriched WHERE package_id = ?", (package_id,)).fetchone()
    if not row:
        row = conn.execute("SELECT * FROM packages WHERE package_id = ?", (package_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Package not found")

    pkg = dict(row)

    days = conn.execute(
        "SELECT * FROM itinerary_days WHERE package_id = ? ORDER BY day_number",
        (package_id,),
    ).fetchall()
    inclusions = conn.execute(
        "SELECT inclusion_item FROM inclusions WHERE package_id = ?", (package_id,)
    ).fetchall()
    exclusions = conn.execute(
        "SELECT exclusion_item FROM exclusions WHERE package_id = ?", (package_id,)
    ).fetchall()
    accommodation = conn.execute(
        "SELECT * FROM accommodation WHERE package_id = ?", (package_id,)
    ).fetchall()
    conn.close()

    pkg["itinerary"] = [dict(d) for d in days] if days else None
    pkg["itinerary_available"] = bool(days)
    pkg["inclusions"] = [r["inclusion_item"] for r in inclusions]
    pkg["exclusions"] = [r["exclusion_item"] for r in exclusions]
    pkg["accommodation"] = [dict(a) for a in accommodation]

    # Explicit, honest "not available" — no fabricated reviews/trust data
    pkg["reviews_available"] = False
    pkg["rating"] = None
    pkg["total_reviews"] = None
    pkg["trust_insights"] = None

    return pkg


# --- User Auth & Profile Endpoints ---

class LoginInput(BaseModel):
    email: str
    password: str

class GoogleLoginInput(BaseModel):
    credential: str
    role: str = "traveler"

class RegisterInput(BaseModel):
    email: str
    password: str
    role: str = "traveler"
    agency_name: str | None = None

@app.post("/api/auth/register")
def register_user(payload: RegisterInput):
    from scripts.auth_service import create_user
    res = create_user(payload.email, payload.password, payload.role, payload.agency_name)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.post("/api/auth/login")
def login_user(payload: LoginInput):
    from scripts.auth_service import create_session_token, verify_user
    res = verify_user(payload.email, payload.password)
    if not res.get("authenticated"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    res["session_token"] = create_session_token(res)
    return res

@app.get("/api/auth/google-config")
def google_auth_config():
    import os
    return {"client_id": os.getenv("GOOGLE_CLIENT_ID"), "enabled": bool(os.getenv("GOOGLE_CLIENT_ID"))}

@app.post("/api/auth/google")
def google_login(payload: GoogleLoginInput):
    import os
    import httpx
    from scripts.auth_service import create_session_token, create_user, verify_user

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    if payload.role not in {"traveler", "packager"}:
        raise HTTPException(status_code=400, detail="Invalid Google sign-in role.")

    try:
        token_response = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.credential},
            timeout=5,
        )
        token_response.raise_for_status()
        claims = token_response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Google identity could not be verified.") from error

    if claims.get("aud") != client_id or claims.get("email_verified") != "true":
        raise HTTPException(status_code=401, detail="Google identity could not be verified.")

    email = claims.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google did not provide an email address.")

    from scripts.auth_service import get_user_by_email
    existing = get_user_by_email(email)
    if payload.role == "packager":
        if not existing or existing["role"] not in {"packager", "admin"}:
            raise HTTPException(status_code=403, detail="This Google account is not registered as a packager.")
        user = existing
    elif existing:
        user = existing
    else:
        created = create_user(email, f"google:{claims.get('sub')}", role="traveler")
        user = get_user_by_email(email) if created.get("status") == "success" else None

    if not user:
        raise HTTPException(status_code=500, detail="Could not create the Google account.")
    user["session_token"] = create_session_token(user)
    user["authenticated"] = True
    return user

class ProfileSettingsInput(BaseModel):
    user_id: str = "U001"
    home_location: str | None = None
    personalization_enabled: bool | None = None
    avoided_preferences: list[str] | None = None


class TripHistoryInput(BaseModel):
    user_id: str = "U001"
    package_id: str | None = None
    destinations: list[str] | str
    start_location: str | None = None
    travel_date: str | None = None
    duration_days: int | None = None
    budget_spent_inr: float | None = None
    travelers: int | None = None
    themes: list[str] | None = None
    pace: str | None = None
    transport: str | None = None
    user_rating: float | None = None
    user_feedback: str | None = ""
    liked: list[str] | None = None
    disliked: list[str] | None = None
    source: str = "manual_entry"


class NextTripRequest(BaseModel):
    user_id: str = "U001"
    mode: str = "preferences"  # preferences, something_new, similar_last
    top_k: int = 6


@app.get("/api/user/profile")
def get_profile(user_id: str = "U001"):
    from scripts.user_profile import get_user_profile
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/api/user/profile")
def update_profile(payload: ProfileSettingsInput):
    from scripts.user_profile import update_user_profile_settings
    settings = payload.dict(exclude_none=True)
    return update_user_profile_settings(user_id=payload.user_id, settings=settings)


@app.delete("/api/user/profile/reset")
def reset_profile_history(user_id: str = "U001"):
    from scripts.user_profile import reset_user_history
    return reset_user_history(user_id)


@app.get("/api/user/trips")
def get_user_trips(user_id: str = "U001"):
    from scripts.trip_history import get_trip_history
    return {"trips": get_trip_history(user_id)}


@app.post("/api/user/trips", status_code=201)
def log_completed_trip(payload: TripHistoryInput):
    from scripts.trip_history import add_completed_trip
    trip_data = payload.dict()
    saved = add_completed_trip(trip_data, user_id=payload.user_id)
    return {"message": "Trip logged successfully", "trip": saved}


@app.delete("/api/user/trips/{trip_id}")
def delete_trip(trip_id: str, user_id: str = "U001"):
    from scripts.trip_history import delete_trip_entry
    return delete_trip_entry(trip_id=trip_id, user_id=user_id)


@app.post("/api/next-trip-suggestions")
def next_trip_suggestions(req: NextTripRequest):
    from scripts.next_trip import get_next_trip_suggestions
    return get_next_trip_suggestions(user_id=req.user_id, mode=req.mode, top_k=req.top_k)

