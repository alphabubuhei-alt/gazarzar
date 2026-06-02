from fastapi import APIRouter, Depends
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
    total_agents = db.query(AgentProfile).count()
    
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
    agents_query = db.query(AgentProfile).all()
    agents_data = []
    for a in agents_query:
        agents_data.append({
            "id": a.id,
            "name": a.user.name if a.user else "Unknown",
            "company": "Үл хөдлөх хөрөнгийн зуучлал", # Default
            "listings_count": len(a.user.listings) if a.user else 0,
            "rating": a.rating
        })

    return {
        "total_listings": total_listings,
        "active_listings": active_listings,
        "boosted_listings": boosted_listings,
        "total_users": total_users,
        "total_agents": total_agents,
        "revenue_this_month": revenue_this_month,
        "listings": listings_data,
        "agents": agents_data
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
            "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else None,
        })
    return {"users": result, "total": len(result)}
