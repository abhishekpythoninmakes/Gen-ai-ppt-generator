from sqlalchemy import text
from database import engine

conn = engine.connect()
tables = [row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
print("Tables:", tables)

if "generation_jobs" in tables:
    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(generation_jobs)"))]
    print("generation_jobs columns:", cols)
else:
    print("generation_jobs table NOT found")

conn.close()
