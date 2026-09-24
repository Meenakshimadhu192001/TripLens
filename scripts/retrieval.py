"""
TripLens - Semantic Candidate Retrieval

Queries ChromaDB / lexical retrieval for candidate packages, hydrated
with feature data from packages_enriched.

Explicit destination constraints are strictly enforced so semantic search
never overrides the user's chosen destination.
"""

import os
import re
import sqlite3

from config.ranking_weights import RETRIEVAL_TOP_K


DB_PATH = "database/triplens.db"
CHROMA_PATH = "database/chroma_db"

_collection = None


def _get_db_path():
    """
    Find the SQLite database from the current working directory
    or relative to this script.
    """
    for candidate in [
        DB_PATH,
        os.path.join(os.path.dirname(__file__), "..", DB_PATH),
        os.path.join("..", DB_PATH),
    ]:
        if os.path.exists(candidate):
            return candidate

    return DB_PATH


def _get_collection():
    """
    Load ChromaDB only when semantic search is enabled
    and ChromaDB is available.
    """
    global _collection

    if _collection is None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            client = chromadb.PersistentClient(
                path=CHROMA_PATH
            )

            embedding_func = (
                embedding_functions
                .SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            )

            _collection = client.get_or_create_collection(
                name="travel_packages",
                embedding_function=embedding_func,
            )

        except Exception:
            _collection = None

    return _collection


def build_semantic_query(
    prefs: dict,
    original_prompt: str
) -> str:
    """
    Use the user's original prompt for semantic retrieval.
    """
    return original_prompt


def _get_table_info(conn):
    """
    Use the canonical packages table for live retrieval.

    packages_enriched is a generated snapshot and can lag behind packages
    after a manager submission, which would hide newly created packages.
    """
    return False, "packages"


def _find_destination_packages(
    conn,
    table_name: str,
    destination: str
):
    """
    Find packages that belong to the requested destination.

    Destination can appear in:
    - packages.destinations
    - package_name
    - accommodation.destination
    - itinerary_days.stops
    - itinerary_days.activities
    """

    destination = destination.strip().lower()

    # UI labels can describe a region using the places users actually mean.
    # Search each meaningful place token so "Himachal (Shimla/Manali)" works
    # the same way as a direct "Shimla" or "Manali" request.
    destination_terms = [
        term.strip()
        for term in re.split(r"[,()/]+", destination)
        if len(term.strip()) >= 3
    ]
    if not destination_terms:
        destination_terms = [destination]

    if not destination:
        return []

    clauses = []
    params = []
    for term in destination_terms:
        pattern = f"%{term}%"
        clauses.append("""
            LOWER(COALESCE(p.destinations, '')) LIKE ?
            OR LOWER(COALESCE(p.package_name, '')) LIKE ?
            OR p.package_id IN (
                SELECT a.package_id
                FROM accommodation a
                WHERE LOWER(COALESCE(a.destination, '')) LIKE ?
            )
            OR p.package_id IN (
                SELECT i.package_id
                FROM itinerary_days i
                WHERE LOWER(COALESCE(i.stops, '')) LIKE ?
                   OR LOWER(COALESCE(i.activities, '')) LIKE ?
            )
        """)
        params.extend([pattern] * 5)

    query = f"""
        SELECT DISTINCT p.*
        FROM {table_name} p
        WHERE ({' OR '.join(clauses)})
    """

    cur = conn.cursor()

    return cur.execute(
        query,
        params,
    ).fetchall()


def _score_lexical_match(
    pkg: dict,
    tokens: set
) -> float:
    """
    Calculate a simple lexical relevance score.
    """

    pkg["theme_clean"] = str(
        pkg.get("theme") or ""
    ).lower().strip()

    pkg["itinerary_pace_inferred"] = (
        pkg.get("itinerary_pace")
        or "Moderate"
    )

    searchable = " ".join(
        str(pkg.get(key) or "")
        for key in (
            "package_name",
            "destinations",
            "theme_clean",
            "suited_for",
            "itinerary_pace_inferred",
            "start_location",
        )
    ).lower()

    matches = sum(
        token in searchable
        for token in tokens
    )

    return matches / max(len(tokens), 1)


def get_candidates(
    prefs: dict,
    original_prompt: str,
    top_k: int = RETRIEVAL_TOP_K
) -> list:
    """
    Retrieve candidate packages.

    IMPORTANT:
    If the user explicitly provides a destination,
    only packages related to that destination are allowed.

    Semantic search must never replace an explicit destination
    with an unrelated destination.
    """

    query_text = build_semantic_query(
        prefs,
        original_prompt
    )

    dest_pref = (
        prefs.get("destination_region") or ""
    ).strip()

    db_file = _get_db_path()

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    has_enriched, table_name = _get_table_info(conn)

    # ---------------------------------------------------------
    # CASE 1: User explicitly specified a destination
    # ---------------------------------------------------------

    if dest_pref:

        destination_rows = _find_destination_packages(
            conn,
            table_name,
            dest_pref
        )

        # -----------------------------------------------------
        # IMPORTANT:
        # Destination requested but no package exists.
        #
        # DO NOT search the entire database.
        # Otherwise Goa could return Himachal packages.
        # -----------------------------------------------------

        if not destination_rows:
            conn.close()
            return []

        candidates = []

        tokens = {
            token
            for token in re.findall(
                r"[a-zA-Z]{3,}",
                query_text.lower()
            )
        }

        for row in destination_rows:

            pkg = dict(row)

            pkg["semantic_similarity"] = (
                _score_lexical_match(
                    pkg,
                    tokens
                )
            )

            candidates.append(pkg)

        # -----------------------------------------------------
        # Optional Chroma semantic scoring
        # -----------------------------------------------------

        if (
            os.getenv(
                "TRIPLENS_USE_SEMANTIC_RETRIEVAL"
            ) == "1"
        ):

            collection = _get_collection()

            if collection is not None:

                try:

                    chroma_results = collection.query(
                        query_texts=[query_text],
                        n_results=min(
                            top_k * 3,
                            50
                        ),
                    )

                    chroma_ids = (
                        chroma_results["ids"][0]
                    )

                    chroma_distances = (
                        chroma_results["distances"][0]
                    )

                    similarity_map = {
                        package_id: max(
                            0.0,
                            1.0 - distance
                        )
                        for package_id, distance
                        in zip(
                            chroma_ids,
                            chroma_distances
                        )
                    }

                    for pkg in candidates:

                        package_id = pkg.get(
                            "package_id"
                        )

                        if package_id in similarity_map:

                            pkg["semantic_similarity"] = (
                                similarity_map[
                                    package_id
                                ]
                            )

                except Exception:
                    pass

        conn.close()

        candidates.sort(
            key=lambda pkg:
                pkg.get(
                    "semantic_similarity",
                    0.0
                ),
            reverse=True
        )

        return candidates[:top_k]

    # ---------------------------------------------------------
    # CASE 2: No destination was specified
    # ---------------------------------------------------------

    conn.close()

    # ---------------------------------------------------------
    # Semantic ChromaDB retrieval
    # ---------------------------------------------------------

    if (
        os.getenv(
            "TRIPLENS_USE_SEMANTIC_RETRIEVAL"
        ) == "1"
    ):

        collection = _get_collection()

        if collection is not None:

            try:

                results = collection.query(
                    query_texts=[query_text],
                    n_results=top_k,
                )

                ids = results["ids"][0]

                distances = results["distances"][0]

                similarity_by_id = {
                    package_id: max(
                        0.0,
                        1.0 - distance
                    )
                    for package_id, distance
                    in zip(
                        ids,
                        distances
                    )
                }

                if ids:

                    conn = sqlite3.connect(
                        db_file
                    )

                    conn.row_factory = (
                        sqlite3.Row
                    )

                    # Check table again because this
                    # connection is newly opened.
                    _, table_name = _get_table_info(
                        conn
                    )

                    placeholders = ",".join(
                        "?"
                        for _ in ids
                    )

                    rows = conn.execute(
                        f"""
                        SELECT *
                        FROM {table_name}
                        WHERE package_id IN (
                            {placeholders}
                        )
                        """,
                        ids,
                    ).fetchall()

                    conn.close()

                    candidates = []

                    for row in rows:

                        pkg = dict(row)

                        pkg["semantic_similarity"] = (
                            similarity_by_id.get(
                                pkg["package_id"],
                                0.0
                            )
                        )

                        candidates.append(pkg)

                    candidates.sort(
                        key=lambda pkg:
                            pkg.get(
                                "semantic_similarity",
                                0.0
                            ),
                        reverse=True
                    )

                    return candidates[:top_k]

            except Exception:
                pass

    # ---------------------------------------------------------
    # Lexical fallback
    # ---------------------------------------------------------

    return _get_lexical_candidates(
        query_text,
        top_k
    )


def _get_lexical_candidates(
    query_text: str,
    top_k: int
) -> list:
    """
    Lexical fallback when ChromaDB semantic retrieval
    is disabled or unavailable.
    """

    tokens = {
        token
        for token in re.findall(
            r"[a-zA-Z]{3,}",
            query_text.lower()
        )
    }

    db_file = _get_db_path()

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    _, table_name = _get_table_info(conn)

    rows = conn.execute(
        f"SELECT * FROM {table_name}"
    ).fetchall()

    conn.close()

    scored = []

    for row in rows:

        pkg = dict(row)

        pkg["semantic_similarity"] = (
            _score_lexical_match(
                pkg,
                tokens
            )
        )

        scored.append(pkg)

    scored.sort(
        key=lambda pkg:
            pkg.get(
                "semantic_similarity",
                0.0
            ),
        reverse=True
    )

    return scored[:top_k]


if __name__ == "__main__":

    from scripts.preference_extraction import (
        extract_preferences
    )

    sample = (
        "I want a relaxed 5-day Kerala trip "
        "from Kochi for 2 people under ₹30,000 "
        "with beaches, nature and sightseeing."
    )

    print("\nPROMPT:")
    print(sample)

    prefs = extract_preferences(sample)

    print("\nEXTRACTED PREFERENCES:")
    print(prefs)

    print("\nCANDIDATES:")

    candidates = get_candidates(
        prefs,
        sample,
        top_k=5
    )

    if not candidates:
        print("No matching packages found.")

    else:

        for candidate in candidates:

            print(
                candidate.get("package_id"),
                "|",
                candidate.get("package_name"),
                "| dest:",
                candidate.get("destinations"),
                "| sim:",
                round(
                    candidate.get(
                        "semantic_similarity",
                        0.0
                    ),
                    3
                ),
                "| price:",
                candidate.get("price")
            )