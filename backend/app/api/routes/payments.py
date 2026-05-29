import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.models import Listing, Payment, BoostStatus, User

router = APIRouter(prefix="/payments", tags=["payments"])

BOOST_PRICE = 5000  # ₮
BOOST_DAYS = 7

class BoostRequest(BaseModel):
    listing_id: int

# ── QPay helpers ──────────────────────────────────────
async def get_qpay_token() -> str:
    """Get QPay access token using merchant credentials."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.QPAY_BASE_URL}/auth/token",
            auth=(settings.QPAY_USERNAME, settings.QPAY_PASSWORD)
        )
        r.raise_for_status()
        return r.json()["access_token"]

async def create_qpay_invoice(token: str, invoice_id: str, listing_id: int) -> dict:
    """Create QPay invoice and return QR + deeplinks."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.QPAY_BASE_URL}/invoice",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "invoice_code": settings.QPAY_INVOICE_CODE,
                "sender_invoice_no": invoice_id,
                "invoice_receiver_code": "terminal",
                "invoice_description": f"GazarZar Boost — зар #{listing_id}",
                "amount": BOOST_PRICE,
                "callback_url": f"https://yourdomain.mn/api/payments/qpay-callback?invoice_id={invoice_id}"
            }
        )
        r.raise_for_status()
        return r.json()

async def check_qpay_payment(token: str, invoice_id: str) -> bool:
    """Check if QPay invoice has been paid."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.QPAY_BASE_URL}/payment/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"object_type": "INVOICE", "object_id": invoice_id}
        )
        data = r.json()
        return data.get("count", 0) > 0

# ── Endpoints ─────────────────────────────────────────
@router.post("/boost/create")
async def create_boost_invoice(
    body: BoostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a QPay invoice for boosting a listing."""
    listing = db.query(Listing).filter(
        Listing.id == body.listing_id,
        Listing.owner_id == current_user.id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Зар олдсонгүй")

    import uuid
    invoice_id = f"GZ-{uuid.uuid4().hex[:10].upper()}"

    # Demo mode: skip real QPay when credentials not set
    if not settings.QPAY_USERNAME:
        payment = Payment(
            listing_id=body.listing_id,
            user_id=current_user.id,
            invoice_id=invoice_id,
            amount=BOOST_PRICE,
            status="pending"
        )
        db.add(payment)
        db.commit()
        return {
            "demo": True,
            "invoice_id": invoice_id,
            "amount": BOOST_PRICE,
            "qr_image": None,
            "urls": []
        }

    try:
        token = await get_qpay_token()
        qpay_data = await create_qpay_invoice(token, invoice_id, body.listing_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"QPay холбогдоогүй: {str(e)}")

    payment = Payment(
        listing_id=body.listing_id,
        user_id=current_user.id,
        invoice_id=invoice_id,
        amount=BOOST_PRICE,
        status="pending"
    )
    db.add(payment)
    db.commit()

    return {
        "invoice_id": invoice_id,
        "amount": BOOST_PRICE,
        "qr_image": qpay_data.get("qr_image"),
        "urls": qpay_data.get("urls", [])
    }


@router.post("/boost/check/{invoice_id}")
async def check_boost_payment(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Poll to check if payment succeeded, then activate boost."""
    payment = db.query(Payment).filter(
        Payment.invoice_id == invoice_id,
        Payment.user_id == current_user.id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice олдсонгүй")
    if payment.status == "paid":
        return {"paid": True}

    paid = False
    if settings.QPAY_USERNAME:
        try:
            token = await get_qpay_token()
            paid = await check_qpay_payment(token, invoice_id)
        except Exception:
            pass
    # Demo: auto-confirm after 3 checks (handled on frontend timer)

    if paid:
        payment.status = "paid"
        listing = db.query(Listing).filter(Listing.id == payment.listing_id).first()
        if listing:
            listing.boost_status = BoostStatus.active
            listing.boost_expires_at = datetime.now(timezone.utc) + timedelta(days=BOOST_DAYS)
        db.commit()
        return {"paid": True}

    return {"paid": False}


@router.post("/qpay-callback")
async def qpay_callback(invoice_id: str, db: Session = Depends(get_db)):
    """Webhook from QPay when payment completes."""
    payment = db.query(Payment).filter(Payment.invoice_id == invoice_id).first()
    if payment and payment.status != "paid":
        payment.status = "paid"
        listing = db.query(Listing).filter(Listing.id == payment.listing_id).first()
        if listing:
            listing.boost_status = BoostStatus.active
            listing.boost_expires_at = datetime.now(timezone.utc) + timedelta(days=BOOST_DAYS)
        db.commit()
    return {"ok": True}
