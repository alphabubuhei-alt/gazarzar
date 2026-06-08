from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import AgentProfile, User, Listing

router = APIRouter(prefix="/agents", tags=["agents"])

def agent_to_dict(a: AgentProfile) -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "name": a.user.name if a.user else None,
        "phone": a.user.phone if a.user else None,
        "bio": a.bio,
        "avatar_url": a.avatar_url,
        "cover_url": a.cover_url,
        "years_exp": a.years_exp,
        "districts": a.districts.split(",") if a.districts else [],
        "badge": a.badge,
        "total_sales": a.total_sales,
        "rating": a.rating,
        "review_count": a.review_count,
    }

@router.get("/")
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(AgentProfile).all()
    return {"items": [agent_to_dict(a) for a in agents]}

@router.get("/{agent_id}")
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    a = db.query(AgentProfile).filter(AgentProfile.id == agent_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Агент олдсонгүй")
    data = agent_to_dict(a)
    data["reviews"] = [
        {"name": r.reviewer_name, "stars": r.stars, "text": r.text,
         "date": r.created_at.strftime("%Y-%m-%d")}
        for r in a.reviews
    ]
    data["listings"] = []
    if a.user:
        for l in a.user.listings[:5]:
            primary = next((img.url for img in l.images if img.is_primary), None)
            data["listings"].append({
                "id": l.id, "title": l.title, "price": l.price,
                "rooms": l.rooms, "area": l.area, "district": l.district,
                "primary_image": primary
            })
    return data


from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user

class AgentApplyRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None

@router.post("/apply")
def apply_agent(
    body: AgentApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.models import UserRole
    current_user.role = UserRole.agent_pending
    if body.name:
        current_user.name = body.name
    # Create or update profile
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if not profile:
        profile = AgentProfile(user_id=current_user.id, bio=body.bio, badge="new")
        db.add(profile)
    else:
        profile.bio = body.bio
    db.commit()
    return {"message": "Агент болох хүсэлт илгээгдлээ"}
