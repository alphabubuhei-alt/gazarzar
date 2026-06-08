import os, uuid, shutil
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
        pass # Not an image or compression failed

@router.post("/listing/{listing_id}/images")
async def upload_images(
    listing_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.owner_id == current_user.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй эсвэл эрх байхгүй")

    existing_count = db.query(ListingImage).filter(ListingImage.listing_id == listing_id).count()
    if existing_count + len(files) > 10:
        raise HTTPException(status_code=400, detail="Дээд тал нь 10 медиа файл оруулах боломжтой")

    saved_urls = []
    folder = os.path.join(settings.UPLOAD_DIR, str(listing_id))
    os.makedirs(folder, exist_ok=True)

    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"{f.filename}: Файлын төрөл зөвшөөрөгдөхгүй")
        
        content = await f.read()
        if len(content) > MAX_BYTES * 2: # Give videos more space (double the image limit)
            raise HTTPException(status_code=400, detail=f"{f.filename}: Файлын хэмжээ хэтэрлээ")

        ext = os.path.splitext(f.filename)[1].lower()
        if not ext: ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(folder, filename)
        
        with open(filepath, "wb") as out:
            out.write(content)
        
        if f.content_type.startswith("image/"):
            compress_image(filepath)

        is_primary = existing_count == 0 and len(saved_urls) == 0
        order = existing_count + len(saved_urls)
        img_obj = ListingImage(listing_id=listing_id, url=f"/uploads/{listing_id}/{filename}", is_primary=is_primary, order=order)
        db.add(img_obj)
        saved_urls.append(img_obj.url)

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
    
    # Save folder
    folder = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(folder, exist_ok=True)
    
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext: ext = ".jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(folder, filename)
    
    with open(filepath, "wb") as out:
        out.write(content)
        
    if file.content_type.startswith("image/"):
        compress_image(filepath, max_width=400) # Avatars can be smaller
        
    url = f"/uploads/avatars/{filename}"
    
    # Also update in DB directly
    from app.models.models import AgentProfile
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if not profile:
        profile = AgentProfile(user_id=current_user.id, bio="", badge="new")
        db.add(profile)
    profile.avatar_url = url
    db.commit()
    
    return {"url": url}
