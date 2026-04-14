from sqlalchemy import text
from database import engine

conn = engine.connect()

# Check generation_jobs columns
cols = [row[1] for row in conn.execute(text("PRAGMA table_info(generation_jobs)"))]
print("generation_jobs columns:", cols)

# Add missing columns
needed = {
    "prompt": "TEXT",
    "num_slides": "INTEGER DEFAULT 6",
    "slide_width": "INTEGER DEFAULT 960",
    "slide_height": "INTEGER DEFAULT 540",
}

for col_name, col_type in needed.items():
    if col_name not in cols:
        print(f"Adding column: {col_name}")
        conn.execute(text(f"ALTER TABLE generation_jobs ADD COLUMN {col_name} {col_type}"))
        conn.commit()
    else:
        print(f"Column {col_name} already exists")

# Verify
cols2 = [row[1] for row in conn.execute(text("PRAGMA table_info(generation_jobs)"))]
print("Updated columns:", cols2)

conn.close()
print("Done!")
