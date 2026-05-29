import os
import random
import sys
from datetime import datetime, timezone

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models.models import (
    User, AgentProfile, Listing, ListingImage,
    UserRole, ListingType, ListingStatus, BoostStatus
)

def seed():
    print("Database seeding started...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if we already have data
    if db.query(User).count() > 0:
        print("Data already exists. Skipping seed.")
        db.close()
        return

    # 1. Create Users
    users_data = [
        {"phone": "99111111", "name": "Админ Бат", "role": UserRole.admin},
        {"phone": "88111111", "name": "Агент Болд", "role": UserRole.agent},
        {"phone": "88222222", "name": "Агент Сараа", "role": UserRole.agent},
        {"phone": "99000000", "name": "Энгийн Хэрэглэгч", "role": UserRole.user},
    ]
    
    users = []
    for ud in users_data:
        u = User(phone=ud["phone"], name=ud["name"], role=ud["role"])
        db.add(u)
        users.append(u)
    
    db.commit()
    for u in users:
        db.refresh(u)

    admin_user, agent1, agent2, normal_user = users

    # 2. Create Agent Profiles
    a1 = AgentProfile(
        user_id=agent1.id,
        bio="Улаанбаатар хотын шилдэг агент. 10 жилийн туршлагатай.",
        avatar_url="https://i.pravatar.cc/150?u=bold",
        years_exp=10,
        districts="БЗД,СБД,ЧД",
        badge="top",
        total_sales=120,
        rating=5.0
    )
    a2 = AgentProfile(
        user_id=agent2.id,
        bio="Тансаг зэрэглэлийн орон сууцны мэргэжилтэн.",
        avatar_url="https://i.pravatar.cc/150?u=saraa",
        years_exp=5,
        districts="ХУД,СБД",
        badge="verified",
        total_sales=45,
        rating=4.8
    )
    db.add_all([a1, a2])
    db.commit()

    # 3. Create Listings
    titles = ["Зайсанд 3 өрөө орон сууц", "Хотын төвд тохилог 2 өрөө", "Шинэ ашиглалтад орсон хаус", "1 өрөө байр түрээслүүлнэ", "Оффисын талбай зарна"]
    addresses = ["ХУД, Зайсан", "СБД, 1-р хороо", "БЗД, 26-р хороо", "СХД, 5-р хороо", "ЧД, Бага тойруу"]
    images = [
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1512917774-0991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=800&q=80"
    ]

    listings = []
    for i in range(1, 21):
        owner = agent1 if i % 3 == 0 else (agent2 if i % 3 == 1 else normal_user)
        l_type = ListingType.sale if i % 5 != 0 else ListingType.rent
        boost = BoostStatus.active if i % 4 == 0 else BoostStatus.none
        
        lat = 47.915 + (random.random() - 0.5) * 0.1
        lng = 106.915 + (random.random() - 0.5) * 0.1
        
        l = Listing(
            owner_id=owner.id,
            title=f"{random.choice(titles)} #{i}",
            description="Маш тохилог, дулаахан, бүх үйлчилгээндээ ойр.",
            listing_type=l_type,
            status=ListingStatus.active,
            district=random.choice(addresses).split(',')[0],
            address=random.choice(addresses),
            lat=lat,
            lng=lng,
            rooms=random.randint(1, 4),
            area=random.randint(30, 200),
            price=random.randint(50_000_000, 800_000_000) if l_type == ListingType.sale else random.randint(1_000_000, 5_000_000),
            category=random.choice(["apartment", "house", "land", "yard_house"]),
            boost_status=boost
        )
        db.add(l)
        listings.append(l)

    db.commit()
    for l in listings:
        db.refresh(l)

    # 4. Add Images
    for i, l in enumerate(listings):
        img_url = images[i % len(images)]
        img = ListingImage(listing_id=l.id, url=img_url, is_primary=True)
        db.add(img)
    
    db.commit()

    print(f"Seeding completed successfully! Added {len(users)} users, 2 agents, and {len(listings)} listings.")
    db.close()

if __name__ == "__main__":
    seed()
