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
    role: str

# ── Helpers ──────────────────────────────────────────
def normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))

async def send_sms(phone: str, code: str):
    provider = settings.SMS_PROVIDER.lower()
    
    if provider == "mock":
        # Mock mode prints OTP to console and returns it as demo_code
        print(f"[SMS MOCK] Phone: +976{phone} | OTP: {code}")
        return code
        
    elif provider == "twilio":
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_PHONE_NUMBER:
            print("[SMS Twilio Error] Twilio configuration values are missing. Falling back to MOCK mode.")
            print(f"[SMS MOCK] Phone: +976{phone} | OTP: {code}")
            return code
            
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Twilio-оор Монгол улс руу илгээхийн тулд +976 дугаар ашиглана
            recipient = f"+976{phone}"
            message = client.messages.create(
                body=f"GazarZar нэвтрэх код: {code}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=recipient
            )
            print(f"[SMS Twilio] Sent to {recipient} | Message SID: {message.sid}")
        except Exception as e:
            print(f"[SMS Twilio Error] Twilio send error: {e}")
            # Алдаа гарвал DEMO кодыг буцааж хөгжүүлэлтийг тасалдуулахгүй байх
            return code
            
    elif provider == "mocean":
        if settings.SMS_API_KEY and settings.SMS_API_SECRET:
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
                    print(f"[SMS Mocean] Sent to +976{phone} | Status: {resp.status_code} | Response: {resp.text}")
            except Exception as e:
                print(f"[SMS Mocean Error] MoceanAPI send error: {e}")
                return code
        else:
            print("[SMS Mocean Error] MoceanAPI configuration not found.")
            return code
            
    else:
        # Defaults to MOCK if provider is unknown
        print(f"[SMS MOCK - Unknown Provider '{provider}'] Phone: +976{phone} | OTP: {code}")
        return code
        
    return None

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

    sent_code = await send_sms(phone, code)
    
    response_data = {"message": "OTP илгээлээ", "phone": phone}
    if sent_code:
        response_data["demo_code"] = sent_code  # DEMO зорилгоор
        
    return response_data


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(body.phone)

    # Check if the code looks like a Firebase ID Token (JWT is usually long, e.g. > 100 chars)
    if len(body.code) > 6:
        from app.core.firebase import verify_firebase_token
        try:
            firebase_phone_raw = verify_firebase_token(body.code)
            firebase_phone = normalize_phone(firebase_phone_raw)
            # Firebase phone format is "+97699001122". We get last 8 digits for Mongolian numbers.
            if firebase_phone.startswith("976") and len(firebase_phone) > 8:
                firebase_phone = firebase_phone[-8:]
            elif len(firebase_phone) > 8:
                # Fallback if phone code is different but contains Mongolian number
                firebase_phone = firebase_phone[-8:]

            if firebase_phone != phone:
                raise HTTPException(status_code=400, detail="Утасны дугаар таарахгүй байна")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Standard local OTP verification (Backward compatibility for debug/mock)
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
        role = "admin" if phone == "99910230" else "user"
        user = User(phone=phone, role=role)
        db.add(user)
    elif phone == "99910230" and user.role != "admin":
        user.role = "admin"

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.phone, "user_id": user.id})
    return TokenResponse(access_token=token, user_id=user.id, phone=user.phone, name=user.name, role=user.role.value)



from app.core.security import get_current_user

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns current user info - requires auth token"""
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "name": current_user.name,
        "role": current_user.role.value
    }


# ── Simple phone login (no OTP) ───────────────────────
class PhoneLoginRequest(BaseModel):
    phone: str

@router.post("/phone-login", response_model=TokenResponse)
async def phone_login(body: PhoneLoginRequest, db: Session = Depends(get_db)):
    """
    OTP-гүй, зөвхөн утасны дугаараар нэвтрэх.
    Хэрэглэгч байхгүй бол автоматаар шинээр үүсгэнэ.
    """
    phone = normalize_phone(body.phone)
    if len(phone) < 8:
        raise HTTPException(status_code=400, detail="Утасны дугаар буруу байна")

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        role = "admin" if phone == "99910230" else "user"
        user = User(phone=phone, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif phone == "99910230" and user.role != "admin":
        user.role = "admin"
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.phone, "user_id": user.id})
    return TokenResponse(access_token=token, user_id=user.id, phone=user.phone, name=user.name, role=user.role.value)
