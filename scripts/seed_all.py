"""Seed both the SQLite database and the RAG knowledge base."""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, SessionLocal, Base
from app.models import User, Product, Order, OrderItem, Review
from app.rag import ingest_file

Path("data").mkdir(exist_ok=True)
Path("docs").mkdir(exist_ok=True)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ---- users ----
users = []
for i, (name, email, country) in enumerate([
    ("Abebe Tadesse", "abebe@example.com", "Ethiopia"),
    ("Sara Mohammed", "sara.m@example.com", "Ethiopia"),
    ("Liya Kebede", "liya.k@example.com", "Ethiopia"),
    ("John Smith", "john@example.com", "USA"),
    ("Maria Garcia", "maria@example.com", "Spain"),
    ("Yuki Tanaka", "yuki@example.com", "Japan"),
    ("Chen Wei", "chen@example.com", "China"),
    ("Amira Hassan", "amira@example.com", "Egypt"),
], start=1):
    u = User(id=i, name=name, email=email, country=country,
             joined_at=datetime.utcnow() - timedelta(days=random.randint(30, 400)))
    db.add(u); users.append(u)

# ---- products ----
products_data = [
    ("Wireless Headphones", "Electronics", 129.99, 45),
    ("Mechanical Keyboard", "Electronics", 89.50, 30),
    ("Ergonomic Mouse", "Electronics", 49.99, 60),
    ("Cotton T-Shirt", "Apparel", 24.99, 200),
    ("Running Shoes", "Footwear", 119.00, 25),
    ("Coffee Maker", "Home", 79.99, 18),
    ("Desk Lamp", "Home", 34.50, 42),
    ("Backpack 30L", "Travel", 64.99, 50),
    ("Yoga Mat", "Fitness", 29.99, 80),
    ("Water Bottle 1L", "Fitness", 14.99, 150),
]
products = []
for i, (name, cat, price, stock) in enumerate(products_data, start=1):
    p = Product(id=i, name=name, category=cat, price=price, stock=stock,
                description=f"High-quality {name.lower()} for everyday use.")
    db.add(p); products.append(p)

# ---- orders + items ----
order_id = 1
for user in users:
    n_orders = random.randint(1, 5)
    for _ in range(n_orders):
        items = random.sample(products, k=random.randint(1, 3))
        total = 0.0
        order = Order(id=order_id, user_id=user.id, total=0, status="completed",
                      created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180)))
        db.add(order)
        for prod in items:
            qty = random.randint(1, 3)
            it = OrderItem(order_id=order_id, product_id=prod.id,
                           quantity=qty, unit_price=prod.price)
            db.add(it)
            total += qty * prod.price
        order.total = round(total, 2)
        order_id += 1

# ---- reviews ----
review_id = 1
for prod in products:
    n_reviews = random.randint(2, 6)
    for _ in range(n_reviews):
        user = random.choice(users)
        r = Review(id=review_id, product_id=prod.id, user_id=user.id,
                   rating=random.choices([3, 4, 5], weights=[1, 3, 6])[0],
                   comment=random.choice([
                       "Great product, highly recommend!",
                       "Works as expected, good value.",
                       "Decent quality, shipping was fast.",
                       "Better than I expected.",
                       "Solid build, would buy again.",
                   ]),
                   created_at=datetime.utcnow() - timedelta(days=random.randint(1, 120)))
        db.add(r); review_id += 1

db.commit()
print(f"✓ Database seeded: {len(users)} users, {len(products)} products, "
      f"{order_id-1} orders, {review_id-1} reviews")

# ---- RAG docs ----
DOCS = {
    "return_policy.md": """# Return Policy

Customers may return most products within 30 days of delivery for a full refund.
Items must be unused, in original packaging, with all tags attached.

Exclusions: personal care items, custom orders, and clearance items are non-returnable.

To initiate a return, contact support with your order number. Refunds are processed
within 5-7 business days after we receive the returned item.

Return shipping is free for defective products. For buyer-remorse returns, the customer
pays return shipping.
""",
    "shipping_policy.md": """# Shipping Policy

Standard shipping: 3-5 business days, free on orders over $50.
Express shipping: 1-2 business days, $14.99 flat rate.
International shipping: 7-14 business days, calculated at checkout.

Orders placed before 2pm local time ship same day. Tracking numbers are emailed
within 24 hours of shipment.
""",
    "warranty.md": """# Product Warranty

All electronics carry a 1-year manufacturer warranty covering defects in materials
and workmanship. Apparel and accessories carry a 90-day warranty.

Warranty does not cover:
- Normal wear and tear
- Accidental damage
- Misuse or improper care
- Unauthorized repairs

To claim warranty, email warranty@example.com with proof of purchase.
""",
    "loyalty_program.md": """# Loyalty Program

Earn 1 point per $1 spent. 100 points = $5 discount.
Tiers:
- Bronze (0-499 points): 1x earning
- Silver (500-1499 points): 1.5x earning + free shipping
- Gold (1500+ points): 2x earning + free express shipping + birthday gift

Points never expire as long as you make at least one purchase per year.
""",
}

for name, content in DOCS.items():
    path = Path("docs") / name
    path.write_text(content, encoding="utf-8")
    n = ingest_file(str(path), doc_type="policy")
    print(f"✓ Indexed {name}: {n} chunks")

db.close()
print("\nSeed complete. Run: uvicorn app.main:app --reload --port 8000")
