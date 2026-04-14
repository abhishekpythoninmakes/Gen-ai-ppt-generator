from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth_router, ppt_router, settings_router, export_router, admin_router, templates_router, feedback_router
from sqlalchemy import text
from models import User, UserSettings
from auth import hash_password

# Create all tables
Base.metadata.create_all(bind=engine)


def _ensure_is_admin_column():
    # Add is_admin column if missing (SQLite only)
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
        if "is_admin" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()


def _ensure_settings_columns():
    """Add new columns to user_settings if missing (SQLite migration)."""
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(user_settings)"))]
        if "openai_api_key" not in cols:
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN openai_api_key VARCHAR(500) DEFAULT ''"))
            conn.commit()
        if "selected_llm_model" not in cols:
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN selected_llm_model VARCHAR(100) DEFAULT 'groq/llama-3.3-70b-versatile'"))
            conn.commit()


def _ensure_generation_job_columns():
    """Add token tracking columns to generation_jobs if missing."""
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(generation_jobs)"))]
        migrations = {
            "prompt_tokens": "INTEGER DEFAULT 0",
            "completion_tokens": "INTEGER DEFAULT 0",
            "total_tokens": "INTEGER DEFAULT 0",
            "model_used": "VARCHAR(100) DEFAULT ''",
            "cost_usd": "REAL DEFAULT 0.0",
        }
        for col_name, col_type in migrations.items():
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE generation_jobs ADD COLUMN {col_name} {col_type}"))
                conn.commit()


def _ensure_default_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                email="admin@local",
                username="admin",
                password_hash=hash_password("admin123"),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            settings = UserSettings(user_id=admin.id)
            db.add(settings)
            db.commit()
        elif not admin.is_admin:
            admin.is_admin = True
            db.commit()
    finally:
        db.close()


def _ensure_feedback_columns():
    """Add feedback_rules_json to user_settings and create user_feedback table if needed."""
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(user_settings)"))]
        if "feedback_rules_json" not in cols:
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN feedback_rules_json TEXT DEFAULT '{}'"))
            conn.commit()


_ensure_is_admin_column()
_ensure_settings_columns()
_ensure_generation_job_columns()
_ensure_feedback_columns()
_ensure_default_admin()

app = FastAPI(
    title="AI PPT Generator API",
    description="AI-powered presentation generator and editor",
    version="1.0.0",
)

# CORS — allow Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router.router)
app.include_router(ppt_router.router)
app.include_router(settings_router.router)
app.include_router(export_router.router)
app.include_router(admin_router.router)
app.include_router(templates_router.router)
app.include_router(feedback_router.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "AI PPT Generator API is running"}
