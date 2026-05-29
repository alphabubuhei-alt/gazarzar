import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random

# Add parent directory to path to import app
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.database import SessionLocal, engine, Base
from app.models.models import User, Listing, ListingImage, ListingType, ListingStatus, BoostStatus, UserRole, AgentProfile

def seed():
    db = SessionLocal()
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)

        # Clear existing data to start fresh as requested for "5 each"
        db.query(ListingImage).delete()
        db.query(Listing).delete()
        db.query(AgentProfile).delete()
        db.query(User).delete()
        db.commit()

        # 1. Create Users
        # Agent User
        agent_user = User(phone="99112233", name="Г.Болд (Агент)", role=UserRole.agent)
        db.add(agent_user)
        # Normal User
        normal_user = User(phone="88001122", name="Энгийн Хэрэглэгч", role=UserRole.user)
        db.add(normal_user)
        db.commit()
        db.refresh(agent_user)
        db.refresh(normal_user)

        # Agent Profile
        agent_profile = AgentProfile(
            user_id=agent_user.id,
            bio="Мэргэжлийн үл хөдлөх хөрөнгийн зуучлагч.",
            years_exp=5,
            districts="ХУД, БЗД, СБД",
            badge="verified",
            rating=4.9
        )
        db.add(agent_profile)
        db.commit()

        # 2. Define Locations
        locations = [
            {"name": "Улаанбаатар", "lat": 47.915, "lng": 106.915},
            {"name": "Эрдэнэт", "lat": 49.033, "lng": 104.050},
            {"name": "Дархан", "lat": 49.483, "lng": 105.950},
        ]

        images = [
            "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80"
        ]

        # 3. Add Listings
        listing_configs = [
            {"count": 5, "boost": BoostStatus.active, "role": UserRole.agent, "title_prefix": "BOOST - "},
            {"count": 5, "boost": BoostStatus.none, "role": UserRole.agent, "title_prefix": "АГЕНТ - "},
            {"count": 5, "boost": BoostStatus.none, "role": UserRole.user, "title_prefix": "ЭНГИЙН - "},
        ]

        for config in listing_configs:
            owner = agent_user if config["role"] == UserRole.agent else normal_user
            for i in range(config["count"]):
                loc = random.choice(locations)
                # Jitter location slightly
                lat = loc["lat"] + (random.random() - 0.5) * 0.05
                lng = loc["lng"] + (random.random() - 0.5) * 0.05
                
                l = Listing(
                    owner_id=owner.id,
                    title=f"{config['title_prefix']} {loc['name']} {i+1}",
                    description=f"Энэ бол {loc['name']} хотод байрлах маш гоё үл хөдлөх хөрөнгө юм. {i+1}",
                    listing_type=ListingType.sale,
                    status=ListingStatus.active,
                    district=loc["name"],
                    address=f"{loc['name']}, {i+1}-р хороолол",
                    lat=lat,
                    lng=lng,
                    rooms=random.randint(1, 5),
                    area=random.randint(40, 250),
                    price=random.randint(100, 1500) * 1000000, # 100M to 1.5B
                    boost_status=config["boost"]
                )
                db.add(l)
                db.commit()
                db.refresh(l)

                # Add image
                img = ListingImage(
                    listing_id=l.id,
                    url=random.choice(images),
                    is_primary=True
                )
                db.add(img)
                db.commit()

        print("Successfully seeded 15 listings (5 Boost, 5 Agent, 5 Normal) across UB, Erdenet, Darkhan.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
