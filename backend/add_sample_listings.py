import sqlite3
import random
import os

# Get path to DB
db_path = os.path.join(os.path.dirname(__file__), 'gazarzar.db')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Districts and coords for randomness
districts = [
    ("Хан-Уул", 47.88, 106.90),
    ("Баянзүрх", 47.92, 106.95),
    ("Сүхбаатар", 47.93, 106.92),
    ("Чингэлтэй", 47.94, 106.91),
    ("Баянгол", 47.91, 106.88),
    ("Сонгинохайрхан", 47.93, 106.83)
]

# Images
img_urls = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1580587767303-9b99e69465c0?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1493666438817-866a91353ca9?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1515263487990-61b07816b324?auto=format&fit=crop&w=800&q=80"
]

def add_batch(listing_type, count):
    titles_sale = ["Орон сууц зарна", "Хаус зарна", "Газар зарна", "Зуслангийн байшин зарна", "Оффис зарна"]
    titles_rent = ["Орон сууц түрээслүүлнэ", "Оффис түрээслүүлнэ", "Хаус түрээслүүлнэ", "Үйлчилгээний талбай", "Агуулах түрээслүүлнэ"]
    
    for i in range(count):
        dist_name, base_lat, base_lng = random.choice(districts)
        lat = base_lat + random.uniform(-0.02, 0.02)
        lng = base_lng + random.uniform(-0.02, 0.02)
        
        title = random.choice(titles_sale if listing_type == 'sale' else titles_rent) + f" {random.randint(1, 1000)}"
        price = random.randint(100, 2000) * 1000000 if listing_type == 'sale' else random.randint(1, 10) * 1000000
        area = random.randint(30, 500)
        rooms = random.randint(1, 5)
        
        cursor.execute("""
            INSERT INTO listings (
                title, description, listing_type, district, lat, lng, rooms, area, price, owner_id, 
                status, boost_status, is_new_building, view_count, created_at, updated_at
            ) VALUES (?, 'Тохилог сайхан байрлалтай.', ?, ?, ?, ?, ?, ?, ?, 1, 'active', 'none', 0, 0, datetime('now'), datetime('now'))
        """, (title, listing_type, dist_name, lat, lng, rooms, area, price))
        
        listing_id = cursor.lastrowid
        cursor.execute("INSERT INTO listing_images (listing_id, url, is_primary, 'order') VALUES (?, ?, 1, 0)", (listing_id, random.choice(img_urls)))

# Add 5 for Sale and 5 for Rent
add_batch('sale', 5)
add_batch('rent', 5)

conn.commit()
conn.close()
print("10 new listings (5 sale, 5 rent) added successfully!")
