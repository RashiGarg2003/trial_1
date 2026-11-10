"""Builds a Northwind-style SQLite sales database (synthetic, seeded, reproducible).

Includes a deliberately planted business problem so root-cause analysis has something to find:
  * Q4-2024: Electronics sales in Europe fall sharply (fewer orders + deeper discounting on remaining ones).
"""
import random
from pathlib import Path
import sqlite3
from datetime import date, timedelta

import config

random.seed(42)

CATEGORIES = ["Electronics", "Furniture", "Clothing", "Groceries", "Sports"]
PRODUCTS = {  # category -> [(name, price, cost)]
    "Electronics": [("Laptop", 900, 650), ("Smartphone", 600, 420), ("Headphones", 120, 70), ("Smartwatch", 250, 160)],
    "Furniture": [("Office Chair", 180, 100), ("Desk", 320, 190), ("Bookshelf", 140, 80)],
    "Clothing": [("Jacket", 95, 45), ("Jeans", 60, 28), ("Sneakers", 85, 40), ("T-Shirt", 20, 8)],
    "Groceries": [("Coffee Beans", 14, 8), ("Olive Oil", 11, 7), ("Pasta Pack", 5, 2.5)],
    "Sports": [("Yoga Mat", 30, 14), ("Dumbbell Set", 75, 40), ("Running Shoes", 110, 60)],
}
REGIONS = {
    "North America": ["USA", "Canada", "Mexico"],
    "Europe": ["Germany", "France", "UK", "Spain"],
    "Asia Pacific": ["Japan", "Australia", "India", "Singapore"],
    "Latin America": ["Brazil", "Argentina", "Chile"],
}
SEGMENTS = ["Consumer", "Corporate", "Small Business"]
REGION_WEIGHT = {"North America": 0.38, "Europe": 0.30, "Asia Pacific": 0.22, "Latin America": 0.10}

SCHEMA = """
CREATE TABLE categories (category_id INTEGER PRIMARY KEY, category_name TEXT NOT NULL);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id), unit_price REAL NOT NULL, unit_cost REAL NOT NULL);
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL, segment TEXT,
    country TEXT, region TEXT);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL, ship_country TEXT);
CREATE TABLE order_items (order_item_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id), quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL, discount REAL NOT NULL DEFAULT 0);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);
"""


def build(path=config.DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)

    cat_ids, products = {}, []
    for i, c in enumerate(CATEGORIES, 1):
        conn.execute("INSERT INTO categories VALUES (?,?)", (i, c))
        cat_ids[c] = i
    pid = 1
    for c, items in PRODUCTS.items():
        for name, price, cost in items:
            conn.execute("INSERT INTO products VALUES (?,?,?,?,?)", (pid, name, cat_ids[c], price, cost))
            products.append((pid, c, price))
            pid += 1

    customers = []
    for cid in range(1, 401):
        region = random.choices(list(REGION_WEIGHT), weights=list(REGION_WEIGHT.values()))[0]
        country = random.choice(REGIONS[region])
        conn.execute("INSERT INTO customers VALUES (?,?,?,?,?)",
                     (cid, f"Customer {cid:03d}", random.choice(SEGMENTS), country, region))
        customers.append((cid, region, country))

    oid, iid = 1, 1
    start, end = date(2023, 1, 1), date(2024, 12, 31)
    d = start
    while d <= end:
        months_in = (d.year - 2023) * 12 + d.month - 1
        season = 1.35 if d.month in (11, 12) else 1.0
        n_orders = int(random.gauss(14, 3) * (1 + 0.015 * months_in) * season)
        for _ in range(max(n_orders, 3)):
            cid, region, country = random.choice(customers)
            conn.execute("INSERT INTO orders VALUES (?,?,?,?)", (oid, cid, d.isoformat(), country))
            for _ in range(random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]):
                p_id, cat, price = random.choice(products)
                disc = random.choice([0, 0, 0, 0.05, 0.10])
                qty = random.randint(1, 4)
                # ---- planted anomaly: Europe / Electronics collapse in Q4 2024 ----
                if region == "Europe" and cat == "Electronics" and d >= date(2024, 10, 1):
                    if random.random() < 0.55:
                        continue
                    disc = random.choice([0.15, 0.20, 0.25])
                    qty = random.randint(1, 2)
                conn.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?)", (iid, oid, p_id, qty, price, disc))
                iid += 1
            oid += 1
        d += timedelta(days=1)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    print(f"Created {path} with {n} orders and {iid-1} order lines.")


if __name__ == "__main__":
    build()
