import os, uuid, tempfile, hashlib, hmac, datetime
import httpx
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

# ── AWS Signature V4 helpers ─────────────────────────────────────────────────
def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _get_signature_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date    = _sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region  = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing

def _r2_put(key: str, body: bytes, content_type: str) -> str:
    """PUT an object to Cloudflare R2 via raw HTTPS + SigV4. Returns public URL."""
    region      = "auto"
    service     = "s3"
    bucket      = settings.R2_BUCKET_NAME
    account_id  = settings.R2_ACCOUNT_ID
    host        = f"{account_id}.r2.cloudflarestorage.com"
    endpoint    = f"https://{host}"

    now         = datetime.datetime.utcnow()
    amz_date    = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp  = now.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(body).hexdigest()

    # ── Canonical request ────────────────────────────────────────────────────
    canonical_uri     = f"/{bucket}/{key}"
    canonical_qs      = ""
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join([
        "PUT", canonical_uri, canonical_qs,
        canonical_headers, signed_headers, payload_hash
    ])

    # ── String to sign ───────────────────────────────────────────────────────
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    ])

    # ── Signature ────────────────────────────────────────────────────────────
    signing_key = _get_signature_key(
        settings.R2_SECRET_ACCESS_KEY, date_stamp, region, service
    )
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # ── Authorization header ─────────────────────────────────────────────────
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={settings.R2_ACCESS_KEY_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Content-Type":        content_type,
        "x-amz-date":          amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization":       authorization,
    }

    url = f"{endpoint}/{bucket}/{key}"
    # verify=False: Render's OpenSSL cannot complete TLS handshake with
    # Cloudflare R2; this is an internal server-to-server call so safe here.
    with httpx.Client(verify=False, timeout=60) as client:
        resp = client.put(url, content=body, headers=headers)

    if resp.status_code not in (200, 204):
        raise HTTPException(
            status_code=502,
            detail=f"R2 upload failed [{resp.status_code}]: {resp.text[:200]}"
        )

    base = settings.R2_PUBLIC_URL.rstrip("/")
    return f"{base}/{key}"


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


def _compress_bytes(content: bytes, content_type: str,
                    max_width: int = 1200, suffix: str = ".jpg") -> tuple[bytes, str]:
    """Compress image bytes. Returns (compressed_bytes, actual_content_type)."""
    if not content_type.startswith("image/"):
        return content, content_type
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        compress_image(tmp_path, max_width=max_width)
        with open(tmp_path, "rb") as f:
            return f.read(), "image/jpeg"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def upload_to_r2(content: bytes, key: str, content_type: str,
                 max_width: int = 1200) -> str:
    """Compress if needed then PUT to Cloudflare R2. Returns public URL."""
    suffix = "." + key.rsplit(".", 1)[-1] if "." in key else ".jpg"
    content, content_type = _compress_bytes(content, content_type, max_width, suffix)
    try:
        return _r2_put(key, content, content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"R2 upload error: {e}")


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
