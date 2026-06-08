from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.models import Listing, ListingImage, SavedListing, User, ListingType, ListingStatus, BoostStatus
from datetime import datetime, timezone

router = APIRouter(prefix="/listings", tags=["listings"])

# ── Schemas ──────────────────────────────────────────
class ListingOut(BaseModel):
    id: int
    title: str
    listing_type: str
    status: str
    district: Optional[str]
    khoroo: Optional[str]
    address: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    rooms: Optional[int]
    bathrooms: Optional[int]
    area: Optional[float]
    floor: Optional[int]
    total_floors: Optional[int]
    price: Optional[float]
    category: Optional[str] = None
    boost_status: str
    is_new_building: bool
    view_count: int
    primary_image: Optional[str] = None
    owner_name: Optional[str] = None
    owner_role: Optional[str] = "user"
    owner_agent_profile_id: Optional[int] = None

    class Config:
        from_attributes = True

class ListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    listing_type: str = "sale"
    district: Optional[str] = None
    khoroo: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    price: Optional[float] = None
    category: Optional[str] = None
    is_new_building: bool = False
    boost_status: Optional[str] = "normal"

class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    listing_type: Optional[str] = None
    district: Optional[str] = None
    khoroo: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    price: Optional[float] = None
    category: Optional[str] = None
    is_new_building: Optional[bool] = None

# ── Helper ───────────────────────────────────────────
def listing_to_dict(l: Listing) -> dict:
    primary = next((img.url for img in l.images if img.is_primary), None)
    if not primary and l.images:
        primary = l.images[0].url
    return {
        "id": l.id,
        "title": l.title,
        "listing_type": l.listing_type.value,
        "status": l.status.value,
        "district": l.district,
        "khoroo": l.khoroo,
        "address": l.address,
        "lat": l.lat,
        "lng": l.lng,
        "rooms": l.rooms,
        "bathrooms": l.bathrooms,
        "area": l.area,
        "floor": l.floor,
        "total_floors": l.total_floors,
        "price": l.price,
        "category": l.category,
        "boost_status": l.boost_status.value,
        "is_new_building": l.is_new_building,
        "view_count": l.view_count,
        "primary_image": primary,
        "owner_name": l.owner.name if (l.owner and l.owner.name) else (l.owner.phone if l.owner else None),
        "owner_phone": l.owner.phone if l.owner else None,
        "owner_role": l.owner.role.value if l.owner else "user",
        "owner_avatar": l.owner.agent_profile.avatar_url if (l.owner and l.owner.agent_profile) else None,
        "owner_agent_profile_id": l.owner.agent_profile.id if (l.owner and l.owner.agent_profile and l.owner.role.value == "agent") else None,
        "created_at": l.created_at.replace(tzinfo=timezone.utc).isoformat() if l.created_at else None,
    }

# ── Endpoints ─────────────────────────────────────────
@router.get("/")
def get_listings(
    type: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    rooms: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query("newest"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    q = db.query(Listing).filter(Listing.status == ListingStatus.active)

    if type in ("sale", "rent"):
        q = q.filter(Listing.listing_type == type)
    from sqlalchemy import or_
    
    if district:
        search_term = district.lower().strip()
        term_map = {
            'ulaanbaatar': 'Улаанбаатар', 'ub': 'Улаанбаатар', 'уб': 'Улаанбаатар',
            'bayanzurkh': 'Баянзүрх', 'bzd': 'Баянзүрх', 'бзд': 'Баянзүрх',
            'khan-uul': 'Хан-Уул', 'khanuul': 'Хан-Уул', 'hud': 'Хан-Уул', 'худ': 'Хан-Уул',
            'sukhbaatar': 'Сүхбаатар', 'sbd': 'Сүхбаатар', 'сбд': 'Сүхбаатар',
            'chingeltei': 'Чингэлтэй', 'chd': 'Чингэлтэй', 'чд': 'Чингэлтэй',
            'bayangol': 'Баянгол', 'bgd': 'Баянгол', 'бгд': 'Баянгол',
            'songinokhairkhan': 'Сонгинохайрхан', 'shd': 'Сонгинохайрхан', 'схд': 'Сонгинохайрхан',
            'nalaikh': 'Налайх', 'nd': 'Налайх', 'нд': 'Налайх',
            'zaisan': 'Зайсан'
        }
        translated = term_map.get(search_term, district)
        q = q.filter(
            or_(
                Listing.district.ilike(f"%{translated}%"),
                Listing.title.ilike(f"%{translated}%"),
                Listing.address.ilike(f"%{translated}%")
            )
        )
    if rooms:
        q = q.filter(Listing.rooms == rooms)
    if min_price is not None:
        q = q.filter(Listing.price >= min_price)
    if max_price is not None:
        q = q.filter(Listing.price <= max_price)
    if min_area is not None:
        q = q.filter(Listing.area >= min_area)
    if max_area is not None:
        q = q.filter(Listing.area <= max_area)
    if category:
        q = q.filter(Listing.category == category)

    # Sort
    if sort == "cheapest":
        q = q.order_by(Listing.price.asc())
    elif sort == "expensive":
        q = q.order_by(Listing.price.desc())
    elif sort == "area":
        q = q.order_by(Listing.area.desc())
    else:  # newest + boosted first
        from sqlalchemy import case
        q = q.order_by(
            case((Listing.boost_status == BoostStatus.active, 0), else_=1),
            Listing.created_at.desc()
        )

    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {"total": total, "items": [listing_to_dict(l) for l in items]}


@router.get("/mine")
def get_my_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Тухайн нэвтэрсэн хэрэглэгчийн өөрийнх нь оруулсан зарууд."""
    items = (
        db.query(Listing)
        .filter(Listing.owner_id == current_user.id)
        .order_by(Listing.created_at.desc())
        .all()
    )
    return {"items": [listing_to_dict(l) for l in items]}


@router.get("/saved")
def get_saved_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Хэрэглэгчийн ♡ дарсан буюу хадгалсан зарууд."""
    saved_rows = (
        db.query(SavedListing)
        .filter(SavedListing.user_id == current_user.id)
        .order_by(SavedListing.saved_at.desc())
        .all()
    )
    listings = [s.listing for s in saved_rows if s.listing]
    return {"items": [listing_to_dict(l) for l in listings]}


@router.get("/{listing_id:int}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй")
    l.view_count += 1
    db.commit()
    data = listing_to_dict(l)
    data["images"] = [img.url for img in sorted(l.images, key=lambda x: x.order)]
    data["description"] = l.description
    return data


@router.post("/")
def create_listing(
    body: ListingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enforce limit of 5 listings for non-admin users
    if current_user.phone != "99910230":
        existing_count = db.query(Listing).filter(Listing.owner_id == current_user.id).count()
        if existing_count >= 5:
            raise HTTPException(status_code=400, detail="Хэрэглэгчийн зар оруулах лимит (5 зар) дүүрсэн байна.")

    listing = Listing(
        owner_id=current_user.id,
        title=body.title,
        description=body.description,
        listing_type=body.listing_type,
        district=body.district,
        khoroo=body.khoroo,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        rooms=body.rooms,
        bathrooms=body.bathrooms,
        area=body.area,
        floor=body.floor,
        total_floors=body.total_floors,
        price=body.price,
        category=body.category,
        is_new_building=body.is_new_building,
        status=ListingStatus.active,
        boost_status=BoostStatus.active if body.boost_status == "boosted" else BoostStatus.none
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "message": "Зар амжилттай үүслээ. Хянагдаж байна."}


@router.post("/{listing_id}/save")
def toggle_save(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(SavedListing).filter(
        SavedListing.user_id == current_user.id,
        SavedListing.listing_id == listing_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"saved": False}
    db.add(SavedListing(user_id=current_user.id, listing_id=listing_id))
    db.commit()
    return {"saved": True}


@router.put("/{listing_id}")
def update_listing(
    listing_id: int,
    body: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй")
    if listing.owner_id != current_user.id and current_user.phone != "99910230":
        raise HTTPException(status_code=403, detail="Энэ зарыг өөрчлөх эрхгүй байна")
    
    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
        
    db.commit()
    db.refresh(listing)
    return {"message": "Зар амжилттай шинэчлэгдлээ", "id": listing.id}


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй")
    if listing.owner_id != current_user.id and current_user.phone != "99910230":
        raise HTTPException(status_code=403, detail="Энэ зарыг устгах эрхгүй байна")
    
    # Cascade delete saved items explicitly to avoid foreign key errors
    db.query(SavedListing).filter(SavedListing.listing_id == listing_id).delete()
    # listing_images is cascaded deleted automatically in models
    db.delete(listing)
    db.commit()
    return {"message": "Зар амжилттай устгагдлаа"}
