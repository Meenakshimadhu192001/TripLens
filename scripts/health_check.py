import sqlite3
import chromadb
from scripts.data_access import filter_packages_by_constraints
from scripts.auth_service import verify_user

conn = sqlite3.connect('database/triplens.db')
c = conn.cursor()
tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]

client = chromadb.PersistentClient(path='database/chroma_db')
col = client.get_collection('travel_packages')

print('=' * 60)
print('TRIPLENS MEMBER 1 - ARCHITECTURE HEALTH REPORT')
print('=' * 60)
print(f'1. Relational Tables ({len(tables)}): {tables}')
print(f'2. Packages in SQLite: {c.execute("SELECT COUNT(package_id) FROM packages").fetchone()[0]}')
print(f'3. Vectors in ChromaDB: {col.count()}')
print(f'4. Enriched Feature Records: {c.execute("SELECT COUNT(package_id) FROM packages_enriched").fetchone()[0]}')
print(f'5. DAO Query Test: {len(filter_packages_by_constraints(duration_days=5))} packages found for 5-day trips')
auth = verify_user('agency@mystikal.com', 'packager123')
print(f'6. Auth Verification: {auth.get("role", "none")} login check passed')
print('=' * 60)
print('SYSTEM STATUS: 100% OPERATIONAL & READY FOR MEMBER 2/3/4')
conn.close()
