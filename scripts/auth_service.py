import os
import sqlite3
import hashlib
import base64
import hmac
import json
import time

DB_PATH = os.path.join("database", "triplens.db")
SESSION_SECRET = os.getenv("TRIPLENS_SESSION_SECRET", "triplens-local-session-secret").encode("utf-8")

def init_user_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('traveler', 'packager', 'admin')),
            agency_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    demo_users = [
        ("traveler@example.com", "pass123", "traveler", None),
        ("agency@mystikal.com", "packager123", "packager", "Mystikal Holidays"),
    ]

    for email, password, role, agency_name in demo_users:
        existing = cursor.execute("SELECT 1 FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO users (email, password_hash, role, agency_name) VALUES (?, ?, ?, ?)",
                (email.strip().lower(), hash_password(password), role, agency_name),
            )

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_user(email, password, role='traveler', agency_name=None):
    init_user_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, agency_name) VALUES (?, ?, ?, ?)",
            (email.strip().lower(), pwd_hash, role, agency_name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "user_id": user_id, "email": email, "role": role}
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "Email already registered"}

def verify_user(email, password):
    init_user_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    cursor.execute(
        "SELECT id, email, role, agency_name FROM users WHERE email = ? AND password_hash = ?",
        (email.strip().lower(), pwd_hash)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"authenticated": True, "id": user[0], "email": user[1], "role": user[2], "agency_name": user[3]}
    return {"authenticated": False, "message": "Invalid credentials"}

def get_user_by_email(email):
    init_user_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, email, role, agency_name FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def create_session_token(user):
    payload = {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "agency_name": user.get("agency_name"),
        "exp": int(time.time()) + 8 * 60 * 60,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(SESSION_SECRET, encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"

def verify_session_token(token):
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None

if __name__ == "__main__":
    init_user_table()
    create_user("agency@mystikal.com", "packager123", role="packager", agency_name="Mystikal Holidays")
    print("[AUTH SERVICE] User table initialized and default packager registered.")
