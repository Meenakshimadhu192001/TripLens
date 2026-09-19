import sqlite3

conn = sqlite3.connect("database/triplens.db")

count = conn.execute(
    "SELECT COUNT(*) FROM packages"
).fetchone()[0]

test = conn.execute(
    "SELECT COUNT(*) FROM packages WHERE package_id = ?",
    ("TEST001",)
).fetchone()[0]

print("PACKAGE COUNT:", count)
print("TEST001 COUNT:", test)

conn.close()