import random
import sqlite3
from datetime import date, timedelta

from app.config import settings

random.seed(7)

CITIES = ["Pune", "Mumbai", "Delhi", "Bengaluru", "Kolhapur", "Nagpur"]
NAMES = ["Aarav", "Diya", "Rohan", "Isha", "Kabir", "Meera", "Arjun", "Sneha", "Vikram", "Anaya",
         "Aditya", "Priya", "Karan", "Neha", "Rahul", "Pooja", "Sahil", "Tanvi", "Yash", "Riya",
         "Manav", "Kavya", "Nikhil", "Sana", "Harsh", "Mira", "Dev", "Ira", "Om", "Tara"]
PRODUCTS = [
    ("Laptop", "Electronics", 55000), ("Smartphone", "Electronics", 22000), ("Headphones", "Electronics", 3000),
    ("Tablet", "Electronics", 30000), ("Office Chair", "Furniture", 8500), ("Desk", "Furniture", 12000),
    ("Bookshelf", "Furniture", 6500), ("Notebook Pack", "Stationery", 250), ("Pen Set", "Stationery", 400),
    ("Backpack", "Accessories", 1800), ("Water Bottle", "Accessories", 600), ("Desk Lamp", "Accessories", 1500),
]
STATUSES = ["delivered"] * 7 + ["shipped"] * 2 + ["cancelled"]

settings.db_path.parent.mkdir(parents=True, exist_ok=True)
if settings.db_path.exists():
    settings.db_path.unlink()  # start fresh every time

con = sqlite3.connect(settings.db_path)
cur = con.cursor()
cur.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT, joined_date TEXT);
CREATE TABLE products  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER);
CREATE TABLE orders    (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), order_date TEXT, status TEXT);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id),
                          product_id INTEGER REFERENCES products(id), quantity INTEGER);
""")

for i, name in enumerate(NAMES, start=1):
    joined = date(2024, 1, 1) + timedelta(days=random.randint(0, 400))
    cur.execute("INSERT INTO customers VALUES (?, ?, ?, ?)", (i, name, random.choice(CITIES), joined.isoformat()))

for i, (name, category, price) in enumerate(PRODUCTS, start=1):
    cur.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (i, name, category, price))

item_id = 1
for order_id in range(1, 201):
    order_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 364))
    cur.execute("INSERT INTO orders VALUES (?, ?, ?, ?)",
                (order_id, random.randint(1, len(NAMES)), order_date.isoformat(), random.choice(STATUSES)))
    for product_id in random.sample(range(1, len(PRODUCTS) + 1), random.randint(1, 3)):
        cur.execute("INSERT INTO order_items VALUES (?, ?, ?, ?)",
                    (item_id, order_id, product_id, random.randint(1, 4)))
        item_id += 1

con.commit()

for table in ["customers", "products", "orders", "order_items"]:
    print(f"{table:12} {cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]} rows")
con.close()
print("Created", settings.db_path)