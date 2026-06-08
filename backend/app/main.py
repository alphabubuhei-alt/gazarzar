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
    allow_origins=["*"], # For production, you may want to restrict this to your domain
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
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@app.get("/api/db-check")
def db_check(db = Depends(get_db)):
    from app.models.models import User, AgentProfile
    users = db.query(User).all()
    profiles = db.query(AgentProfile).all()
    return {
        "users": [{"id": u.id, "phone": u.phone, "name": u.name, "role": u.role.value if hasattr(u.role, "value") else str(u.role)} for u in users],
        "profiles": [{"id": p.id, "user_id": p.user_id, "bio": p.bio} for p in profiles]
    }
