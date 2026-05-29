# GazarZar — Project Status

> **Шинэчлэгдсэн:** 2026-04-25
> **Хувилбар:** v0.2 — Backend суурь бэлэн

---

## 📁 Фолдерын бүтэц

```
gazarzar_app/
├── frontend/
│   └── index.html              ← Claude-ийн бичсэн UI (gazarzar_final_23)
│
└── backend/
    ├── app/
    │   ├── main.py             ← FastAPI entry point
    │   ├── core/
    │   │   ├── config.py       ← Pydantic settings (.env)
    │   │   ├── database.py     ← SQLAlchemy engine + get_db
    │   │   └── security.py     ← JWT token + get_current_user
    │   ├── models/
    │   │   └── models.py       ← DB хүснэгтүүд (бүгд)
    │   └── api/routes/
    │       ├── auth.py         ← POST /api/auth/send-otp, verify-otp
    │       ├── listings.py     ← GET/POST /api/listings
    │       ├── agents.py       ← GET /api/agents
    │       ├── upload.py       ← POST /api/upload/listing/{id}/images
    │       └── payments.py     ← POST /api/payments/boost/*
    ├── uploads/                ← Хэрэглэгчийн зургууд (static)
    ├── requirements.txt
    └── .env.example
```

---

## ✅ Хийгдсэн зүйлс (Gemini / Antigravity)

| # | Файл | Дэлгэрэнгүй |
|---|------|-------------|
| 1 | `core/config.py` | Pydantic Settings, .env уншина |
| 2 | `core/database.py` | SQLite холболт, get_db dependency |
| 3 | `core/security.py` | JWT create/decode, get_current_user, get_optional_user |
| 4 | `models/models.py` | User, OTPCode, Listing, ListingImage, SavedListing, AgentProfile, AgentReview, Payment |
| 5 | `routes/auth.py` | OTP илгээх (demo print), verify → JWT буцаана |
| 6 | `routes/listings.py` | Хайлт (filter, sort, paginate), харах, үүсгэх, хадгалах |
| 7 | `routes/agents.py` | Агентуудын жагсаалт + нэгийг харах |
| 8 | `routes/upload.py` | Зураг оруулах + Pillow compression |
| 9 | `routes/payments.py` | QPay invoice үүсгэх, шалгах, webhook |
| 10 | `app/main.py` | FastAPI app, CORS, бүх route mount |

---

## 🔴 Дараагийн алхам — Claude-д даалгавар

### Claude-д өгөх промпт #1 — Frontend API холболт

```
Сайн байна уу. Бид GazarZar гэдэг Монгол үл хөдлөх хөрөнгийн платформ хөгжүүлж байна.
Gemini (Antigravity) нь FastAPI backend бэлдсэн. API endpoints:

НЭВТРЭХ:
  POST /api/auth/send-otp   body: {"phone": "99001122"}
  POST /api/auth/verify-otp body: {"phone": "99001122", "code": "123456"}
    → response: {"access_token": "...", "user_id": 1, "phone": "...", "name": null}

ЗАРУУД:
  GET  /api/listings?type=sale&district=БЗД&rooms=2&min_price=50000000&sort=newest
  GET  /api/listings/{id}
  POST /api/listings  (Authorization: Bearer <token>)  body: ListingCreate schema
  POST /api/listings/{id}/save  (auth required)

АГЕНТУУД:
  GET /api/agents
  GET /api/agents/{id}

frontend/index.html файл нь одоо бүх өгөгдлийг JavaScript дотор hardcode хийсэн байгаа 
(ALL = [...], AGENTS = [...] гэсэн массивууд).

Даалгавар:
1. index.html дотрох hardcoded ALL массивыг устгаад, 
   /api/listings?type=... рүү fetch() дуудаж өгөгдлийг татна.
2. AGENTS массивыг /api/agents рүү fetch() -ээр солино.
3. sendOTP() функцийг /api/auth/send-otp рүү бодит POST хийдэг болгоно.
4. verOTP() функцийг /api/auth/verify-otp рүү POST хийж, 
   хариу токеныг localStorage-д хадгалдаг болгоно.
5. Зар оруулах submitPost() функцийг /api/listings рүү POST хийдэг болгоно.
6. ♡ дарахад /api/listings/{id}/save рүү POST хийдэг болгоно.

Мөн эдгээрийг нэмнэ:
- const API_BASE = 'http://localhost:8000'  ← файлын эхэнд
- Бүх fetch дуудлагад error handling нэмнэ (try/catch)
- Токен шаардлагатай үед localStorage.getItem('gz_token') ашиглана
- Хэрэглэгч нэвтэрсэн эсэхийг localStorage.getItem('gz_token') -ээр шалгана

Зөвхөн index.html файлын JavaScript хэсгийг өгч байгаарай. HTML болон CSS-ийг бүү өөрчил.
```

---

## 🔧 Backend ажиллуулах команд

```powershell
# 1. Backend фолдер руу орно
cd C:\Users\PC\.gemini\antigravity\scratch\gazarzar_app\backend

# 2. Virtual environment үүсгэнэ
python -m venv venv
venv\Scripts\activate

# 3. Сангуудыг суулгана
pip install -r requirements.txt

# 4. .env файл үүсгэнэ
copy .env.example .env

# 5. Сервер ажиллуулна
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

---

## 📋 Хийгдэх зүйлсийн жагсаалт

- [x] Фолдерын бүтэц
- [x] Database models
- [x] JWT Authentication
- [x] Listings CRUD API
- [x] Agents API
- [x] Image Upload API
- [x] QPay Boost API
- [x] Frontend → API холболт (**Claude-ийн даалгавар**)
- [ ] SMS Gateway (sms.mn) бодит холболт
- [x] Admin dashboard (Separated admin.html with RBAC security)
- [x] Seed data (demo зарууд DB-д)
- [ ] Production deploy

---

## 🔑 Чухал тэмдэглэл

- **Database:** SQLite (файл: `backend/gazarzar.db`) — хөгжүүлэлтэд хангалттай
- **Auth:** JWT token, localStorage-д `gz_token` нэрээр хадгална
- **Demo OTP:** Одоогоор `/api/auth/send-otp` response дотор `demo_code` харагдана → Production-д устгана
- **QPay:** `.env` дотор `QPAY_USERNAME` хоосон байвал demo горимд ажиллана
