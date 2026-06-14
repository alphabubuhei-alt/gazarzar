from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.models import Listing, User, AgentProfile, Payment, ListingStatus, BoostStatus
from app.core.security import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    # 1. Stats
    total_listings = db.query(Listing).count()
    active_listings = db.query(Listing).filter(Listing.status == ListingStatus.active).count()
    boosted_listings = db.query(Listing).filter(Listing.boost_status == BoostStatus.active).count()
    
    total_users = db.query(User).count()
    total_agents = db.query(AgentProfile).join(User).filter(User.role == "agent").count()
    
    # Revenue this month
    now = datetime.now(timezone.utc)
    # Simple filtering for current month revenue
    revenue_query = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "paid",
    ).scalar()
    revenue_this_month = revenue_query or 0

    # 2. Latest Listings
    recent_listings = db.query(Listing).order_by(Listing.created_at.desc()).limit(15).all()
    listings_data = []
    for l in recent_listings:
        listings_data.append({
            "id": l.id,
            "title": l.title,
            "price": l.price,
            "priceVal": l.price,
            "boost_status": l.boost_status.value if l.boost_status else "none",
            "status": l.status.value if l.status else "pending",
        })

    # 3. Agents
    agents_query = db.query(AgentProfile).join(User).filter(User.role == "agent").all()
    agents_data = []
    for a in agents_query:
        agents_data.append({
            "id": a.id,
            "name": a.user.name if a.user else "Unknown",
            "phone": a.user.phone if a.user else "—",
            "company": "Үл хөдлөх хөрөнгийн зуучлал", # Default
            "listings_count": len(a.user.listings) if a.user else 0,
            "rating": a.rating
        })

    # 4. Users
    users_query = db.query(User).order_by(User.id.desc()).all()
    users_data = []
    for u in users_query:
        users_data.append({
            "id": u.id,
            "phone": u.phone,
            "name": u.name or "—",
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
            "listings_count": len(u.listings) if hasattr(u, 'listings') else 0,
            "created_at": u.created_at.replace(tzinfo=timezone.utc).isoformat() if hasattr(u, 'created_at') and u.created_at else None,
        })

    return {
        "total_listings": total_listings,
        "active_listings": active_listings,
        "boosted_listings": boosted_listings,
        "total_users": total_users,
        "total_agents": total_agents,
        "revenue_this_month": revenue_this_month,
        "listings": listings_data,
        "agents": agents_data,
        "users": users_data
    }

@router.post("/listings/{id}/approve")
def approve_listing(
    id: int, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if listing:
        listing.status = ListingStatus.active
        db.commit()
    return {"message": "Амжилттай баталлаа"}

@router.delete("/listings/{id}")
def delete_listing(
    id: int, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if listing:
        db.delete(listing)
        db.commit()
    return {"message": "Амжилттай устгалаа"}


@router.post("/listings/{id}/boost")
def toggle_boost(
    id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if not listing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Зар олдсонгүй")
    if listing.boost_status == BoostStatus.active:
        listing.boost_status = BoostStatus.none
        boosted = False
    else:
        listing.boost_status = BoostStatus.active
        boosted = True
    db.commit()
    return {"boosted": boosted, "boost_status": listing.boost_status.value}


@router.get("/users")
def get_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Бүртгэлтэй хэрэглэгчдийн жагсаалт"""
    users = db.query(User).order_by(User.id.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "phone": u.phone,
            "name": u.name or "—",
            "role": u.role,
            "listings_count": len(u.listings) if hasattr(u, 'listings') else 0,
            "created_at": u.created_at.replace(tzinfo=timezone.utc).isoformat() if hasattr(u, 'created_at') and u.created_at else None,
        })
    return {"users": result, "total": len(result)}


from pydantic import BaseModel
class RoleUpdate(BaseModel):
    role: str

@router.post("/users/{user_id}/set-role")
def set_user_role(
    user_id: int,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    from app.models.models import UserRole
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Хэрэглэгч олдсонгүй")
    
    if body.role == "agent":
        user.role = UserRole.agent
        # Check or create AgentProfile
        profile = db.query(AgentProfile).filter(AgentProfile.user_id == user.id).first()
        if not profile:
            profile = AgentProfile(user_id=user.id, bio="", badge="new")
            db.add(profile)
    elif body.role == "admin":
        user.role = UserRole.admin
    else:
        user.role = UserRole.user
        # Delete AgentProfile if user downgraded
        db.query(AgentProfile).filter(AgentProfile.user_id == user.id).delete()

    db.commit()
    return {"message": "Хэрэглэгчийн эрх өөрчлөгдлөө", "role": user.role.value}


@router.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Агентыг устгах: AgentProfile-г DB-с устгаж, хэрэглэгчийн эрхийг 'user' болгоно"""
    from fastapi import HTTPException
    from app.models.models import UserRole
    profile = db.query(AgentProfile).filter(AgentProfile.id == agent_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Агент олдсонгүй")
    user = profile.user
    # Reset role to regular user
    if user:
        user.role = UserRole.user
    db.delete(profile)
    db.commit()
    return {"message": "Агент амжилттай устгагдлаа"}


@router.post("/migrate-data")
def migrate_data(
    x_migration_secret: str = Header(None),
    db: Session = Depends(get_db)
):
    import httpx
    from app.models.models import UserRole, ListingImage, User, AgentProfile, Listing, ListingStatus, BoostStatus
    
    if x_migration_secret != "gazarzar-super-secret-migration-key":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    migrated_agents = 0
    migrated_listings = 0
    
    with httpx.Client() as client:
        # 1. Migrate agents
        try:
            r = client.get("https://gazarzar-backend.onrender.com/api/agents/")
            if r.status_code == 200:
                agents_list = r.json().get("items", [])
                for a in agents_list:
                    phone = a.get("phone")
                    if not phone:
                        continue
                    
                    # Find or create User
                    user = db.query(User).filter(User.phone == phone).first()
                    if not user:
                        user = User(phone=phone, name=a.get("name"), role=UserRole.agent)
                        db.add(user)
                        db.flush()
                    else:
                        user.role = UserRole.agent
                    
                    # Find or create AgentProfile
                    profile = db.query(AgentProfile).filter(AgentProfile.user_id == user.id).first()
                    avatar = a.get("avatar_url") or a.get("image")
                    if avatar and avatar.startswith("/uploads"):
                        avatar = "https://gazarzar-backend.onrender.com" + avatar
                        
                    cover = a.get("cover_url")
                    if cover and cover.startswith("/uploads"):
                        cover = "https://gazarzar-backend.onrender.com" + cover
                        
                    districts_str = ",".join(a.get("districts", [])) if isinstance(a.get("districts"), list) else (a.get("districts") or "")
                    
                    if not profile:
                        profile = AgentProfile(
                            user_id=user.id,
                            bio=a.get("bio", ""),
                            avatar_url=avatar,
                            cover_url=cover,
                            years_exp=a.get("years_exp", 0),
                            districts=districts_str,
                            badge=a.get("badge", "new"),
                            total_sales=a.get("total_sales", 0),
                            rating=a.get("rating", 0.0),
                            review_count=a.get("review_count", 0)
                        )
                        db.add(profile)
                        migrated_agents += 1
            db.commit()
        except Exception as e:
            db.rollback()
            print("Agent migration error:", e)
            
        # 2. Migrate listings
        try:
            r = client.get("https://gazarzar-backend.onrender.com/api/listings/?limit=100")
            if r.status_code == 200:
                listings_list = r.json().get("items", [])
                for l in listings_list:
                    owner_phone = l.get("owner_phone")
                    if not owner_phone:
                        continue
                    
                    # Check if listing already exists in new DB
                    existing = db.query(Listing).filter(
                        Listing.title == l.get("title"),
                        Listing.price == l.get("price"),
                        Listing.lat == l.get("lat"),
                        Listing.lng == l.get("lng")
                    ).first()
                    if existing:
                        continue
                        
                    # Find or create User
                    owner = db.query(User).filter(User.phone == owner_phone).first()
                    if not owner:
                        owner = User(phone=owner_phone, name=l.get("owner_name"), role=UserRole.agent if l.get("owner_role") == "agent" else UserRole.user)
                        db.add(owner)
                        db.flush()
                        
                    # Get full description from detail page
                    description = ""
                    images_urls = []
                    try:
                        detail_r = client.get(f"https://gazarzar-backend.onrender.com/api/listings/{l.get('id')}")
                        if detail_r.status_code == 200:
                            detail_data = detail_r.json()
                            description = detail_data.get("description", "")
                            images_urls = detail_data.get("images", [])
                    except Exception:
                        pass
                        
                    primary_image = l.get("primary_image")
                    if primary_image and primary_image.startswith("/uploads"):
                        primary_image = "https://gazarzar-backend.onrender.com" + primary_image
                        
                    # Create Listing
                    new_l = Listing(
                        owner_id=owner.id,
                        title=l.get("title", "Зар"),
                        description=description,
                        listing_type=l.get("listing_type", "sale"),
                        status=ListingStatus.active,
                        district=l.get("district"),
                        khoroo=l.get("khoroo"),
                        address=l.get("address"),
                        lat=l.get("lat"),
                        lng=l.get("lng"),
                        rooms=l.get("rooms"),
                        bathrooms=l.get("bathrooms"),
                        area=l.get("area"),
                        floor=l.get("floor"),
                        total_floors=l.get("total_floors"),
                        price=l.get("price"),
                        category=l.get("category"),
                        boost_status=BoostStatus.active if l.get("boost_status") == "active" else BoostStatus.none,
                        is_new_building=l.get("is_new_building", False),
                        view_count=l.get("view_count", 0)
                    )
                    db.add(new_l)
                    db.flush()
                    
                    # Create ListingImages
                    for idx, img_url in enumerate(images_urls):
                        if img_url.startswith("/uploads"):
                            img_url = "https://gazarzar-backend.onrender.com" + img_url
                        is_primary = (img_url == primary_image) or (idx == 0 and not primary_image)
                        db.add(ListingImage(
                            listing_id=new_l.id,
                            url=img_url,
                            is_primary=is_primary,
                            order=idx
                        ))
                    
                    migrated_listings += 1
            db.commit()
        except Exception as e:
            db.rollback()
            print("Listing migration error:", e)
            
    return {
        "status": "success",
        "migrated_agents": migrated_agents,
        "migrated_listings": migrated_listings
    }


@router.get("/diagnose-upload")
def diagnose_upload():
    import os
    from app.core.config import settings
    upload_dir = settings.UPLOAD_DIR
    exists = os.path.exists(upload_dir)
    abspath = os.path.abspath(upload_dir) if exists else None
    files = []
    if exists:
        try:
            for root, dirs, filenames in os.walk(upload_dir):
                for f in filenames:
                    files.append(os.path.relpath(os.path.join(root, f), upload_dir))
        except Exception as e:
            files = [f"Error listing files: {e}"]
            
    # Check /data/uploads persistent disk
    data_uploads_exists = os.path.exists("/data/uploads")
    data_uploads_files = []
    if data_uploads_exists:
        try:
            data_uploads_files = os.listdir("/data/uploads")
        except Exception as e:
            data_uploads_files = [f"Error: {e}"]
            
    env_keys = list(os.environ.keys())
    return {
        "upload_dir": upload_dir,
        "exists": exists,
        "abspath": abspath,
        "files_count": len(files),
        "files": files[:100],
        "data_uploads": {
            "exists": data_uploads_exists,
            "files": data_uploads_files
        },
        "r2_config": {
            "R2_ACCOUNT_ID_set": bool(settings.R2_ACCOUNT_ID),
            "R2_ACCESS_KEY_ID_set": bool(settings.R2_ACCESS_KEY_ID),
            "R2_SECRET_ACCESS_KEY_set": bool(settings.R2_SECRET_ACCESS_KEY),
            "R2_BUCKET_NAME_set": bool(settings.R2_BUCKET_NAME),
            "R2_PUBLIC_URL_set": bool(settings.R2_PUBLIC_URL),
        },
        "env_keys": env_keys
    }

