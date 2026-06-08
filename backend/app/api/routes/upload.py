import os, uuid, tempfile
import boto3
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.models import Listing, ListingImage, User
from PIL import Image

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "video/mp4", "video/webm", "video/quicktime"
}
MAX_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024

# ── Cloudflare R2 setup ──────────────────────────────────────────────────────
USE_R2 = bool(
    settings.R2_ACCOUNT_ID
    and settings.R2_ACCESS_KEY_ID
    and settings.R2_SECRET_ACCESS_KEY
    and settings.R2_PUBLIC_URL
    and settings.R2_BUCKET_NAME
)

_r2_client = None

def get_r2_client():
    global _r2_client
    if _r2_client is None:
        _r2_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _r2_client


# ── Helpers ──────────────────────────────────────────────────────────────────
def compress_image(path: str, max_width: int = 1200) -> None:
    try:
        with Image.open(path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
            img.save(path, "JPEG", quality=82, optimize=True)
    except Exception:
        pass


def upload_to_r2(content: bytes, key: str, content_type: str,
                 max_width: int = 1200) -> str:
    """Upload bytes to Cloudflare R2, return public URL."""
    suffix = "." + key.rsplit(".", 1)[-1] if "." in key else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if content_type.startswith("image/"):
            compress_image(tmp_path, max_width=max_width)

        client = get_r2_client()
        with open(tmp_path, "rb") as f:
            client.upload_fileobj(
                f,
                settings.R2_BUCKET_NAME,
                key,
                ExtraArgs={"ContentType": content_type},
            )

        base = settings.R2_PUBLIC_URL.rstrip("/")
        return f"{base}/{key}"
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cloudflare R2 Upload failed: {str(e)}"
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def save_file_local(content: bytes, subfolder: str, filename: str,
                    content_type: str = "", max_width: int = 1200) -> str:
    """Fallback: local storage (ephemeral on Render free tier)."""
    folder = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    if content_type.startswith("image/"):
        compress_image(filepath, max_width=max_width)
    return f"/uploads/{subfolder}/{filename}"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/listing/{listing_id}/images")
async def upload_images(
    listing_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(
        Listing.id == listing_id,
        Listing.owner_id == current_user.id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй эсвэл эрх байхгүй")

    existing_count = db.query(ListingImage).filter(
        ListingImage.listing_id == listing_id
    ).count()
    if existing_count + len(files) > 10:
        raise HTTPException(status_code=400, detail="Дээд тал нь 10 медиа файл оруулах боломжтой")

    saved_urls = []

    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400,
                detail=f"{f.filename}: Файлын төрөл зөвшөөрөгдөхгүй")

        content = await f.read()
        limit = MAX_BYTES * 2 if f.content_type.startswith("video/") else MAX_BYTES
        if len(content) > limit:
            raise HTTPException(status_code=400,
                detail=f"{f.filename}: Файлын хэмжээ хэтэрлээ")

        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"

        if USE_R2:
            key = f"listings/{listing_id}/{filename}"
            url = upload_to_r2(content, key, f.content_type)
        else:
            url = save_file_local(content, str(listing_id), filename, f.content_type)

        is_primary = existing_count == 0 and len(saved_urls) == 0
        order = existing_count + len(saved_urls)
        img_obj = ListingImage(
            listing_id=listing_id,
            url=url,
            is_primary=is_primary,
            order=order,
        )
        db.add(img_obj)
        saved_urls.append(url)

    db.commit()
    return {"uploaded": len(saved_urls), "urls": saved_urls}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Файлын төрөл зөвшөөрөгдөхгүй")

    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Файлын хэмжээ хэтэрлээ")

    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"

    if USE_R2:
        key = f"avatars/{filename}"
        url = upload_to_r2(content, key, file.content_type, max_width=400)
    else:
        url = save_file_local(content, "avatars", filename, file.content_type, max_width=400)

    # Update AgentProfile in DB
    from app.models.models import AgentProfile
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if not profile:
        profile = AgentProfile(user_id=current_user.id, bio="", badge="new")
        db.add(profile)
    profile.avatar_url = url
    db.commit()

    return {"url": url}
