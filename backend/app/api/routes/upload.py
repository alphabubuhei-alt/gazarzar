import os, uuid, shutil, tempfile
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
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

# ── Cloudinary setup ─────────────────────────────────────────────────────────
USE_CLOUDINARY = bool(
    settings.CLOUDINARY_CLOUD_NAME
    and settings.CLOUDINARY_API_KEY
    and settings.CLOUDINARY_API_SECRET
)

if USE_CLOUDINARY:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )

# ── Helpers ───────────────────────────────────────────────────────────────────
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


def save_file_local(content: bytes, subfolder: str, filename: str) -> str:
    """Save to local uploads dir, return relative URL."""
    folder = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return f"/uploads/{subfolder}/{filename}"


def upload_to_cloudinary(content: bytes, filename: str, content_type: str,
                          folder: str, max_width: int = 1200) -> str:
    """Upload bytes to Cloudinary, return secure URL."""
    # Write to temp file so we can compress images first
    suffix = os.path.splitext(filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if content_type.startswith("image/"):
            compress_image(tmp_path, max_width=max_width)

        resource_type = "video" if content_type.startswith("video/") else "image"
        result = cloudinary.uploader.upload(
            tmp_path,
            folder=f"gazarzar/{folder}",
            resource_type=resource_type,
            quality="auto",
            fetch_format="auto",
        )
        return result["secure_url"]
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

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

    existing_count = db.query(ListingImage).filter(ListingImage.listing_id == listing_id).count()
    if existing_count + len(files) > 10:
        raise HTTPException(status_code=400, detail="Дээд тал нь 10 медиа файл оруулах боломжтой")

    saved_urls = []

    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"{f.filename}: Файлын төрөл зөвшөөрөгдөхгүй")

        content = await f.read()
        limit = MAX_BYTES * 2 if f.content_type.startswith("video/") else MAX_BYTES
        if len(content) > limit:
            raise HTTPException(status_code=400, detail=f"{f.filename}: Файлын хэмжээ хэтэрлээ")

        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"

        if USE_CLOUDINARY:
            url = upload_to_cloudinary(
                content, filename, f.content_type,
                folder=f"listings/{listing_id}"
            )
        else:
            # Local fallback — compress then save
            url = save_file_local(content, str(listing_id), filename)
            local_path = os.path.join(settings.UPLOAD_DIR, str(listing_id), filename)
            if f.content_type.startswith("image/"):
                compress_image(local_path)

        is_primary = existing_count == 0 and len(saved_urls) == 0
        order = existing_count + len(saved_urls)
        img_obj = ListingImage(
            listing_id=listing_id,
            url=url,
            is_primary=is_primary,
            order=order
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
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"

    if USE_CLOUDINARY:
        url = upload_to_cloudinary(
            content, filename, file.content_type,
            folder="avatars", max_width=400
        )
    else:
        url = save_file_local(content, "avatars", filename)
        local_path = os.path.join(settings.UPLOAD_DIR, "avatars", filename)
        if file.content_type.startswith("image/"):
            compress_image(local_path, max_width=400)

    # Update AgentProfile in DB
    from app.models.models import AgentProfile
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if not profile:
        profile = AgentProfile(user_id=current_user.id, bio="", badge="new")
        db.add(profile)
    profile.avatar_url = url
    db.commit()

    return {"url": url}
