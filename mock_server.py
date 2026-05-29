import http.server
import socketserver
import json
import os
import random
from urllib.parse import urlparse, parse_qs

PORT = 8080
DIRECTORY = "frontend"

# ─── Realistic Mock Data ────────────────────────────────────────────────────

AGENTS = [
    {"id": 1, "name": "Г.Болд",   "company": "Remax Mongolia",        "phone": "99001122", "listings_count": 45, "image": "https://i.pravatar.cc/150?u=gbold",    "rating": "5.0", "total_sales": 120, "bio": "10 жилийн туршлагатай, Улаанбаатарын тэргүүлэх брокер.", "badge": "top",      "years_exp": 10, "districts": "БЗД,СБД,ЧД"},
    {"id": 2, "name": "С.Сараа",  "company": "Century 21 Mongolia",   "phone": "88001122", "listings_count": 32, "image": "https://i.pravatar.cc/150?u=ssaraa",   "rating": "4.9", "total_sales": 85,  "bio": "Орон сууц болон арилжааны үл хөдлөх хөрөнгийн мэргэжилтэн.", "badge": "verified", "years_exp": 7,  "districts": "БЗД,БГД"},
    {"id": 3, "name": "Д.Тулга",  "company": "GazarZar LLC",          "phone": "77001122", "listings_count": 12, "image": "https://i.pravatar.cc/150?u=dtulga",   "rating": "4.8", "total_sales": 42,  "bio": "Шинэ орон сууцны байгуулагч болон худалдааны агент.", "badge": "new",      "years_exp": 3,  "districts": "СХД,НД"},
    {"id": 4, "name": "Б.Энхээ",  "company": "Mongolia Real Estate",  "phone": "95112233", "listings_count": 28, "image": "https://i.pravatar.cc/150?u=benkhee",  "rating": "5.0", "total_sales": 67,  "bio": "Хан-Уул болон Баянзүрхийн дагуу газрын мэргэжилтэн.", "badge": "verified", "years_exp": 6,  "districts": "ХУД,БЗД"},
    {"id": 5, "name": "О.Мөнхбаяр","company": "Skyline Properties",  "phone": "96003344", "listings_count": 19, "image": "https://i.pravatar.cc/150?u=omunkh",   "rating": "4.7", "total_sales": 38,  "bio": "Хотын захын болон хувийн байшин худалдааны мэргэжилтэн.", "badge": None,       "years_exp": 4,  "districts": "СБД,ЧД"},
]

AGENT_NAMES = [a["name"] for a in AGENTS]

CITIES = [
    {"name": "Улаанбаатар", "lat": 47.91,  "lng": 106.91, "districts": ["БЗД", "СБД", "ЧД", "БГД", "ХУД", "СХД"]},
    {"name": "Эрдэнэт",     "lat": 49.03,  "lng": 104.04, "districts": ["1-р хороо", "2-р хороо", "3-р хороо"]},
    {"name": "Дархан",      "lat": 49.48,  "lng": 105.92, "districts": ["Дархан", "Зүүн хороо", "Баруун хороо"]},
]

TITLES = [
    "Тохилог 2 өрөө байр",
    "Шинэ ашиглалтанд орсон сууц",
    "Төвд байрлалтай 3 өрөө байр",
    "Хаус, приват хашаатай",
    "Студи байр — Зайсан",
    "4 өрөө том байр, 2 ванн",
    "Шинэ барилга, 1 өрөө",
    "Амарлах зориулалтай байшин",
    "Бизнесийн зориулалтай талбай",
    "VIP сүлжээний байр",
]

IMAGES = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa",
    "https://images.unsplash.com/photo-1512917774-0991f1c4c750",
    "https://images.unsplash.com/photo-1448630360428-65456885c650",
    "https://images.unsplash.com/photo-1515263487990-61b008296ec6",
    "https://images.unsplash.com/photo-1564013799919-ab600027ffc6",
    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c",
    "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b",
    "https://images.unsplash.com/photo-1502005229762-cf1b2da7c5d6",
    "https://images.unsplash.com/photo-1493809842364-78817add7ffb",
]

random.seed(42)

LISTINGS = []
for i in range(1, 61):
    city = CITIES[i % 3]
    district = city["districts"][i % len(city["districts"])]
    lat = city["lat"] + (random.uniform(-0.07, 0.07))
    lng = city["lng"] + (random.uniform(-0.07, 0.07))

    rooms = 1 + (i % 4)
    area = 35 + (i * 7) % 180
    floor = 1 + (i % 12)
    total_floors = floor + (1 + i % 5)
    price = random.randint(80, 900) * 1_000_000

    boost = "active" if i % 8 == 0 else "none"
    is_agent = (i % 3 == 0)
    agent_obj = AGENTS[(i - 1) % len(AGENTS)]
    owner_name = agent_obj["name"] if is_agent else "Хэрэглэгч Бат"
    owner_role = "agent" if is_agent else "user"
    is_new = (i % 6 == 0)

    img_base = IMAGES[i % len(IMAGES)]
    secondary_img = IMAGES[(i + 2) % len(IMAGES)]

    LISTINGS.append({
        "id": i,
        "lat": round(lat, 5),
        "lng": round(lng, 5),
        "price": price,
        "listing_type": "rent" if i % 7 == 0 else "sale",
        "status": "active",
        "rooms": rooms,
        "bathrooms": 1 + (i % 2),
        "area": area,
        "floor": floor,
        "total_floors": total_floors,
        "title": f"{city['name']} — {TITLES[i % len(TITLES)]}",
        "district": district,
        "khoroo": f"{(i % 10) + 1}-р хороо",
        "address": f"{city['name']}, {district}, {(i % 10) + 1}-р хороо",
        "description": (
            f"{city['name']} хотын {district} дүүрэгт байрлалтай, "
            f"нийт {area}м² талбайтай {rooms} өрөө байр. "
            f"{floor}/{total_floors} давхарт. Бүх үйлчилгээндээ ойрхон, "
            f"тайван орчинтой. {'Шинэ барилга.' if is_new else 'Сайн нөхцөлтэй.'}"
        ),
        "primary_image": f"{img_base}?auto=format&fit=crop&w=800&q=80",
        "images": [
            f"{img_base}?auto=format&fit=crop&w=1200&q=80",
            f"{secondary_img}?auto=format&fit=crop&w=1200&q=80",
        ],
        "owner_name": owner_name,
        "owner_role": owner_role,
        "boost_status": boost,
        "is_new_building": is_new,
        "category": random.choice(["apartment", "house", "land", "yard_house"]),
        "view_count": random.randint(5, 500),
    })


# ─── Handler ───────────────────────────────────────────────────────────────

class MockAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def add_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.add_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.add_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        # ── /api/listings ──────────────────────────────────────────────────
        if path.startswith("/api/listings"):
            parts = path.split("/")
            # Single listing  /api/listings/<id>
            if len(parts) >= 4 and parts[3].isdigit():
                lid = int(parts[3])
                item = next((l for l in LISTINGS if l["id"] == lid), None)
                if item:
                    return self.send_json(item)
                return self.send_json({"detail": "Зар олдсонгүй"}, 404)

            # List  /api/listings/
            filtered = LISTINGS[:]

            # filters
            min_p = float(query.get("min_price", [0])[0])
            max_p = float(query.get("max_price", [999_999_999_999])[0])
            filtered = [l for l in filtered if min_p <= l["price"] <= max_p]

            if "district" in query:
                q_raw = query["district"][0].lower().strip()
                filtered = [l for l in filtered
                            if q_raw in l["title"].lower()
                            or q_raw in l["address"].lower()
                            or q_raw in (l["district"] or "").lower()]

            if "rooms" in query:
                r = int(query["rooms"][0])
                if r >= 4:
                    filtered = [l for l in filtered if l["rooms"] >= 4]
                else:
                    filtered = [l for l in filtered if l["rooms"] == r]

            if "min_area" in query:
                filtered = [l for l in filtered if l["area"] >= float(query["min_area"][0])]
            if "max_area" in query:
                filtered = [l for l in filtered if l["area"] <= float(query["max_area"][0])]
            
            if "category" in query:
                cat = query["category"][0].lower()
                filtered = [l for l in filtered if l.get("category") == cat]

            if "listing_type" in query:
                lt = query["listing_type"][0].lower()
                if lt != "all":
                    filtered = [l for l in filtered if l.get("listing_type") == lt]

            # sort
            sort = query.get("sort", ["newest"])[0]
            if sort == "cheapest":
                filtered.sort(key=lambda x: x["price"])
            elif sort == "expensive":
                filtered.sort(key=lambda x: x["price"], reverse=True)
            else:
                filtered.sort(key=lambda x: x["id"], reverse=True)

            # boosted first
            filtered.sort(key=lambda x: x["boost_status"] == "active", reverse=True)

            limit = int(query.get("limit", [50])[0])
            offset = int(query.get("offset", [0])[0])
            page = filtered[offset: offset + limit]
            return self.send_json({"items": page, "total": len(filtered)})

        # ── /api/agents ────────────────────────────────────────────────────
        elif path.startswith("/api/agents"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3].isdigit():
                aid = int(parts[3])
                agent = next((a for a in AGENTS if a["id"] == aid), None)
                if not agent:
                    return self.send_json({"detail": "Агент олдсонгүй"}, 404)
                agent_full = dict(agent)
                # attach listings that belong to this agent
                agent_full["listings"] = [
                    {
                        "id": l["id"], "title": l["title"], "price": l["price"],
                        "rooms": l["rooms"], "area": l["area"],
                        "address": l["address"], "district": l["district"],
                        "primary_image": l["primary_image"],
                        "boost_status": l["boost_status"],
                        "listing_type": l["listing_type"],
                    }
                    for l in LISTINGS if l["owner_name"] == agent["name"]
                ]
                return self.send_json(agent_full)

            return self.send_json({"items": AGENTS, "total": len(AGENTS)})

        # ── /api/admin ─────────────────────────────────────────────────────
        elif path.startswith("/api/admin"):
            stats = {
                "total_listings": len(LISTINGS),
                "active_listings": len([l for l in LISTINGS if l["status"] == "active"]),
                "boosted_listings": len([l for l in LISTINGS if l["boost_status"] == "active"]),
                "total_agents": len(AGENTS),
                "total_users": 142,
                "revenue_this_month": 1_850_000,
                "listings": LISTINGS[:20],
                "agents": AGENTS,
            }
            return self.send_json(stats)

        # ── /api/health ────────────────────────────────────────────────────
        elif path == "/api/health":
            return self.send_json({"status": "ok", "app": "GazarZar Mock", "version": "2.0"})

        # ── Static files ───────────────────────────────────────────────────
        else:
            if path in ("", "/"):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # OTP send
        if "/send-otp" in path:
            return self.send_json({"message": "OTP илгээлээ", "demo_code": "123456"})

        # OTP verify
        if "/verify-otp" in path:
            return self.send_json({
                "access_token": "demo_token_123456",
                "token_type": "bearer",
                "user_id": 1,
                "phone": "99001122",
                "name": "Demo Хэрэглэгч",
                "role": "user"
            })

        # Create listing
        if path == "/api/listings":
            new_id = max(l["id"] for l in LISTINGS) + 1
            import json as _json
            length = int(self.headers.get("Content-Length", 0))
            body = _json.loads(self.rfile.read(length)) if length else {}
            new_listing = {
                "id": new_id,
                "lat": body.get("lat", 47.915),
                "lng": body.get("lng", 106.915),
                "price": float(body.get("price", 0)) * 1_000_000,
                "listing_type": body.get("listing_type", "sale"),
                "status": "active",
                "rooms": body.get("rooms", 1),
                "bathrooms": 1,
                "area": float(body.get("area", 50)),
                "floor": 1,
                "total_floors": 5,
                "title": body.get("title", "Шинэ зар"),
                "district": body.get("district", "Улаанбаатар"),
                "khoroo": "",
                "address": body.get("address", "Улаанбаатар"),
                "description": body.get("description", ""),
                "primary_image": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
                "images": [],
                "owner_name": "Demo Хэрэглэгч",
                "owner_role": "user",
                "boost_status": "none",
                "is_new_building": False,
                "view_count": 0,
            }
            LISTINGS.append(new_listing)
            return self.send_json({"id": new_id, "message": "Зар амжилттай үүслээ."})

        # QPay boost create
        if "/payments/boost/create" in path:
            return self.send_json({
                "demo": True,
                "invoice_id": "GZ-DEMO12345",
                "amount": 5000,
                "qr_image": None,
                "qr_text": "GazarZarBoostDemo",
                "urls": []
            })

        # QPay boost check
        if "/payments/boost/check" in path:
            return self.send_json({"paid": True})

        # Save listing
        if "/save" in path:
            return self.send_json({"saved": True})

        # Admin actions
        if "/api/admin" in path:
            return self.send_json({"ok": True, "message": "Амжилттай"})

        return self.send_json({"status": "ok", "demo": True})

    def log_message(self, fmt, *args):
        # Only log API calls
        if "/api/" in args[0] if args else False:
            super().log_message(fmt, *args)


with socketserver.TCPServer(("", PORT), MockAPIHandler) as httpd:
    print(f"[OK] GazarZar Mock Server running at http://localhost:{PORT}")
    print(f"   API:   http://localhost:{PORT}/api/")
    print(f"   Admin: http://localhost:{PORT}/api/admin")
    httpd.serve_forever()
