from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

class UserRole(str, enum.Enum):
    user = "user"
    agent = "agent"
    admin = "admin"
    agent_pending = "agent_pending"

class ListingType(str, enum.Enum):
    sale = "sale"
    rent = "rent"

class ListingStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    sold = "sold"
    expired = "expired"

class BoostStatus(str, enum.Enum):
    none = "none"
    active = "active"
    expired = "expired"

# ─── USER ───────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(default=UserRole.user)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    listings: Mapped[list["Listing"]] = relationship("Listing", back_populates="owner")
    saved: Mapped[list["SavedListing"]] = relationship("SavedListing", back_populates="user")
    agent_profile: Mapped["AgentProfile | None"] = relationship("AgentProfile", back_populates="user", uselist=False)


# ─── OTP ─────────────────────────────────────────────
class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── LISTING ─────────────────────────────────────────
class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    listing_type: Mapped[ListingType] = mapped_column(default=ListingType.sale)
    status: Mapped[ListingStatus] = mapped_column(default=ListingStatus.pending)

    # Location
    district: Mapped[str | None] = mapped_column(String(50))
    khoroo: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    # Property details
    rooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    area: Mapped[float | None] = mapped_column(Float)
    floor: Mapped[int | None] = mapped_column(Integer)
    total_floors: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(50)) # apartment, house, land, yard_house, office

    # Boost
    boost_status: Mapped[BoostStatus] = mapped_column(default=BoostStatus.none)
    boost_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_new_building: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship("User", back_populates="listings")
    images: Mapped[list["ListingImage"]] = relationship("ListingImage", back_populates="listing", cascade="all, delete-orphan")
    saved_by: Mapped[list["SavedListing"]] = relationship("SavedListing", back_populates="listing")


# ─── LISTING IMAGE ────────────────────────────────────
class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    url: Mapped[str] = mapped_column(String(500))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="images")


# ─── SAVED LISTING ────────────────────────────────────
class SavedListing(Base):
    __tablename__ = "saved_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="saved")
    listing: Mapped["Listing"] = relationship("Listing", back_populates="saved_by")


# ─── AGENT PROFILE ────────────────────────────────────
class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    cover_url: Mapped[str | None] = mapped_column(String(500))
    years_exp: Mapped[int] = mapped_column(Integer, default=0)
    districts: Mapped[str | None] = mapped_column(String(200))  # comma separated e.g. "БЗД,СБД"
    badge: Mapped[str | None] = mapped_column(String(20))       # top | verified | new
    total_sales: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship("User", back_populates="agent_profile")
    reviews: Mapped[list["AgentReview"]] = relationship("AgentReview", back_populates="agent")


# ─── AGENT REVIEW ─────────────────────────────────────
class AgentReview(Base):
    __tablename__ = "agent_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"))
    reviewer_name: Mapped[str] = mapped_column(String(100))
    stars: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent: Mapped["AgentProfile"] = relationship("AgentProfile", back_populates="reviews")


# ─── PAYMENT ──────────────────────────────────────────
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invoice_id: Mapped[str] = mapped_column(String(100), unique=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | paid | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
