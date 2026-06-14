import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.api.routes import auth, listings, agents, upload, payments, admin

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Alter Enum in PostgreSQL to include agent_pending role
from sqlalchemy import text
with engine.connect() as connection:
    try:
        connection.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'agent_pending';")
        )
    except Exception as e:
        pass

# Get the path to index.html relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_PATH = BASE_DIR / "frontend" / "index.html"
ADMIN_PATH = BASE_DIR / "frontend" / "admin.html"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https://(.*\.)?gazarzar\.mn|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?|https://(.*\.)?pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────
app.include_router(auth.router,     prefix="/api")
app.include_router(listings.router, prefix="/api")
app.include_router(agents.router,   prefix="/api")
app.include_router(upload.router,   prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router,    prefix="/api")

# ── Static files (uploaded images) ───────────────────
upload_dir = settings.UPLOAD_DIR
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# ── Serve frontend ────────────────────────────────────
from fastapi.responses import FileResponse

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_PATH))

@app.get("/admin")
def serve_admin():
    return FileResponse(str(ADMIN_PATH))

@app.get("/health")
def health():
    import os
    is_mount = False
    try:
        is_mount = os.path.ismount("/data/uploads")
    except Exception:
        pass
    return {
        "status": "ok", 
        "app": settings.APP_NAME, 
        "version": settings.APP_VERSION,
        "is_mount": is_mount,
        "upload_dir": settings.UPLOAD_DIR
    }


