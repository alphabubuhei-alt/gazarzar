import sys
import os
from sqlalchemy.orm import Session

# Change working directory to backend so database path works
os.chdir("backend")
# Add backend directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.models import Listing, BoostStatus, User, UserRole

def update():
    db = SessionLocal()
    try:
        # Mark first 3 listings as boosted
        listings = db.query(Listing).limit(3).all()
        for i, l in enumerate(listings):
            l.boost_status = BoostStatus.active
        
        # Ensure some listings are by agents and some by normal users
        # The first agent is already there from seed.py
        agent = db.query(User).filter(User.role == UserRole.agent).first()
        if agent:
            # Assign listings 4-6 to this agent
            agent_listings = db.query(Listing).offset(3).limit(3).all()
            for l in agent_listings:
                l.owner_id = agent.id
        
        # Create a normal user for other listings
        normal_user = db.query(User).filter(User.role == UserRole.user).first()
        if not normal_user:
            normal_user = User(phone="88001122", name="Энгийн Хэрэглэгч", role=UserRole.user)
            db.add(normal_user)
            db.commit()
            db.refresh(normal_user)
        
        # Assign other listings to normal user
        normal_listings = db.query(Listing).offset(6).all()
        for l in normal_listings:
            l.owner_id = normal_user.id

        db.commit()
        print("Done updating database.")
    finally:
        db.close()

if __name__ == "__main__":
    update()
