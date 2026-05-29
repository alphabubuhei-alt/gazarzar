import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.models import User, OTPCode
from app.core.config import settings
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Schemas ──────────────────────────────────────────
class SendOTPRequest(BaseModel):
    phone: str  # e.g. "99001122"

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    phone: str
    name: str | None

# ── Helpers ──────────────────────────────────────────
def normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))

async def send_sms(phone: str, code: str):
    if settings.SMS_API_KEY and settings.SMS_API_SECRET and not settings.DEBUG:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    settings.SMS_API_URL,
                    json={
                        "mocean-api-key":    settings.SMS_API_KEY,
                        "mocean-api-secret": settings.SMS_API_SECRET,
                        "mocean-from":       settings.SMS_SENDER,
                        "mocean-to":         f"+976{phone}",
                        "mocean-text":       f"GazarZar нэвтрэх код: {code}"
                    }
                )
                print(f"[SMS] Sent to +976{phone} | Status: {resp.status_code}")
        except Exception as e:
            print(f"[SMS Error] {e}")
    else:
        # DEBUG горимд console-д хэвлэнэ
        print(f"[SMS DEMO] Phone: +976{phone}  OTP: {code}")

# ── Endpoints ─────────────────────────────────────────
@router.post("/send-otp")
async def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(body.phone)
    if len(phone) < 8:
        raise HTTPException(status_code=400, detail="Утасны дугаар буруу байна")

    code = generate_otp()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Invalidate previous OTPs for this phone
    db.query(OTPCode).filter(OTPCode.phone == phone, OTPCode.is_used == False).delete()

    otp = OTPCode(phone=phone, code=code, expires_at=expires)
    db.add(otp)
    db.commit()

    await send_sms(phone, code)
    
    response_data = {"message": "OTP илгээлээ", "phone": phone}
    if settings.DEBUG:
        response_data["demo_code"] = code
        
    return response_data


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(body.phone)
    now = datetime.now(timezone.utc)

    otp = db.query(OTPCode).filter(
        OTPCode.phone == phone,
        OTPCode.code == body.code,
        OTPCode.is_used == False,
        OTPCode.expires_at > now
    ).first()

    if not otp:
        raise HTTPException(status_code=400, detail="Код буруу эсвэл хугацаа дууссан")

    otp.is_used = True

    # Get or create user
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.phone, "user_id": user.id})
    return TokenResponse(access_token=token, user_id=user.id, phone=user.phone, name=user.name)


@router.get("/me")
async def get_me(db: Session = Depends(get_db)):
    """Returns current user info - requires auth token"""
    # Used with get_current_user dependency in main
    pass
