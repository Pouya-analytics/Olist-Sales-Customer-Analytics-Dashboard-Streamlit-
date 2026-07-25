"""
generate_data.py
-----------------
Generates a SYNTHETIC e-commerce transactional dataset whose statistical
properties (customer count, order volume, repeat-purchase rate, review
score distribution, delivery times, category mix) are calibrated to match
the PUBLICLY PUBLISHED statistics of the real Olist Brazilian E-Commerce
dataset (Kaggle, ~100k orders, Sep 2016 - Oct 2018).

This is NOT a copy of the real Olist data. It is a parametrized simulation
built so that the SQL analysis in this project is realistic and reusable.
If you have Kaggle API access, swap this file's output for the real CSVs
(same column names/schema) and every query in /sql runs unchanged.

Why synthetic and disclosed as such: reproducibility without requiring
Kaggle credentials, and honesty about data provenance for anyone auditing
the repo (a recruiter, a freelance client, or a hiring manager).
"""

import random
import sqlite3
import os
from datetime import datetime, timedelta

random.seed(42)  # reproducibility

N_CUSTOMERS = 9600          # 10% scale of real Olist (~96k) for fast local runs
START_DATE = datetime(2016, 9, 1)
END_DATE = datetime(2018, 10, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

# Calibrated to Olist's published category-volume mix (top categories)
CATEGORIES = [
    ("bed_bath_table", 0.10), ("health_beauty", 0.095), ("sports_leisure", 0.085),
    ("furniture_decor", 0.08), ("computers_accessories", 0.075), ("housewares", 0.07),
    ("watches_gifts", 0.06), ("telephony", 0.05), ("garden_tools", 0.045),
    ("auto", 0.04), ("toys", 0.035), ("cool_stuff", 0.03), ("perfumery", 0.03),
    ("baby", 0.025), ("electronics", 0.025), ("stationery", 0.02),
    ("fashion_bags_accessories", 0.02), ("pet_shop", 0.018), ("office_furniture", 0.015),
    ("other", 0.157),
]

STATES = [
    ("SP", 0.42), ("RJ", 0.13), ("MG", 0.12), ("RS", 0.055), ("PR", 0.05),
    ("SC", 0.035), ("BA", 0.035), ("DF", 0.025), ("ES", 0.02), ("GO", 0.02),
    ("PE", 0.015), ("CE", 0.015), ("OTHER", 0.06),
]

PAYMENT_TYPES = [("credit_card", 0.74), ("boleto", 0.19), ("voucher", 0.05), ("debit_card", 0.02)]


def weighted_choice(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


def random_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)),
                              seconds=random.randint(0, 86399))


def build():
    customers = []
    orders = []
    order_items = []
    payments = []
    reviews = []

    order_id_counter = 1
    item_id_counter = 1

    # ---- Customer base with realistic repeat-purchase distribution ----
    # Real Olist: ~97% of customers place exactly 1 order, ~3% place 2+.
    # We replicate that long-tail "mostly one-time buyers" structure,
    # which is THE central fact that makes "churn" analysis meaningful here:
    # in a marketplace with near-zero repeat rate, classic subscription-style
    # churn doesn't apply directly -- you have to redefine churn as
    # "did not return within N days," which the SQL layer demonstrates.
    for cid in range(1, N_CUSTOMERS + 1):
        n_orders = 1
        r = random.random()
        if r > 0.97:
            n_orders = random.choice([2, 2, 2, 3, 3, 4, 5])  # long tail
        state = weighted_choice(STATES)
        signup_date = random_date(START_DATE, END_DATE - timedelta(days=30))
        customers.append({
            "customer_id": f"C{cid:06d}",
            "customer_state": state,
            "first_order_date": signup_date,
        })

        # generate this customer's orders, spaced realistically
        last_date = signup_date
        for i in range(n_orders):
            if i == 0:
                order_date = signup_date
            else:
                # repeat purchase gap: median ~70 days for Olist repeaters
                gap_days = max(1, int(random.gammavariate(2.0, 35)))
                order_date = last_date + timedelta(days=gap_days)
                if order_date > END_DATE:
                    break
            last_date = order_date

            status = "delivered" if random.random() > 0.03 else random.choice(
                ["shipped", "canceled", "unavailable"])

            delivery_days = max(1, int(random.gammavariate(3.0, 4.0)))  # avg ~12 days
            delivered_date = order_date + timedelta(days=delivery_days) if status == "delivered" else None

            order_id = f"O{order_id_counter:07d}"
            order_id_counter += 1

            orders.append({
                "order_id": order_id,
                "customer_id": customers[-1]["customer_id"],
                "order_status": status,
                "order_purchase_timestamp": order_date,
                "order_delivered_timestamp": delivered_date,
                "order_estimated_delivery_date": order_date + timedelta(days=delivery_days + random.randint(-3, 6)),
            })

            # 1-3 items per order (Olist avg ~1.1, slight multi-item tail)
            n_items = 1 if random.random() > 0.18 else random.choice([2, 2, 3])
            for _ in range(n_items):
                category = weighted_choice(CATEGORIES)
                price = round(random.gammavariate(2.2, 45), 2)  # avg ~R$100-160 mix
                freight = round(price * random.uniform(0.05, 0.25), 2)
                order_items.append({
                    "order_item_id": item_id_counter,
                    "order_id": order_id,
                    "product_category": category,
                    "price": price,
                    "freight_value": freight,
                })
                item_id_counter += 1

            pay_type = weighted_choice(PAYMENT_TYPES)
            total_value = sum(it["price"] + it["freight_value"]
                               for it in order_items if it["order_id"] == order_id)
            installments = 1
            if pay_type == "credit_card":
                installments = random.choice([1, 1, 2, 3, 4, 6, 10])
            payments.append({
                "order_id": order_id,
                "payment_type": pay_type,
                "payment_installments": installments,
                "payment_value": round(total_value, 2),
            })

            # Review score: Olist's real distribution is bimodal-skewed:
            # 5:58%, 4:19%, 3:8%, 2:4%, 1:11%
            if status == "delivered":
                score = weighted_choice([(5, 0.58), (4, 0.19), (3, 0.08), (2, 0.04), (1, 0.11)])
            else:
                score = weighted_choice([(1, 0.55), (2, 0.25), (3, 0.15), (4, 0.04), (5, 0.01)])
            review_date = (delivered_date or order_date) + timedelta(days=random.randint(0, 10))
            reviews.append({
                "order_id": order_id,
                "review_score": score,
                "review_creation_date": review_date,
            })

    return customers, orders, order_items, payments, reviews


def write_to_sqlite(customers, orders, order_items, payments, reviews, db_path):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            customer_state TEXT,
            first_order_date TEXT
        )""")
    cur.execute("""
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            order_status TEXT,
            order_purchase_timestamp TEXT,
            order_delivered_timestamp TEXT,
            order_estimated_delivery_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )""")
    cur.execute("""
        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id TEXT,
            product_category TEXT,
            price REAL,
            freight_value REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )""")
    cur.execute("""
        CREATE TABLE payments (
            order_id TEXT,
            payment_type TEXT,
            payment_installments INTEGER,
            payment_value REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )""")
    cur.execute("""
        CREATE TABLE reviews (
            order_id TEXT,
            review_score INTEGER,
            review_creation_date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )""")

    cur.executemany("INSERT INTO customers VALUES (?,?,?)",
                     [(c["customer_id"], c["customer_state"], c["first_order_date"].isoformat())
                      for c in customers])
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)",
                     [(o["order_id"], o["customer_id"], o["order_status"],
                       o["order_purchase_timestamp"].isoformat(),
                       o["order_delivered_timestamp"].isoformat() if o["order_delivered_timestamp"] else None,
                       o["order_estimated_delivery_date"].isoformat())
                      for o in orders])
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)",
                     [(it["order_item_id"], it["order_id"], it["product_category"],
                       it["price"], it["freight_value"]) for it in order_items])
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?)",
                     [(p["order_id"], p["payment_type"], p["payment_installments"], p["payment_value"])
                      for p in payments])
    cur.executemany("INSERT INTO reviews VALUES (?,?,?)",
                     [(r["order_id"], r["review_score"], r["review_creation_date"].isoformat())
                      for r in reviews])

    for stmt in [
        "CREATE INDEX idx_orders_customer ON orders(customer_id)",
        "CREATE INDEX idx_orders_purchase_ts ON orders(order_purchase_timestamp)",
        "CREATE INDEX idx_items_order ON order_items(order_id)",
        "CREATE INDEX idx_payments_order ON payments(order_id)",
        "CREATE INDEX idx_reviews_order ON reviews(order_id)",
    ]:
        cur.execute(stmt)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Generating synthetic dataset (Olist-calibrated distributions)...")
    customers, orders, order_items, payments, reviews = build()
    print(f"  customers:   {len(customers):,}")
    print(f"  orders:      {len(orders):,}")
    print(f"  order_items: {len(order_items):,}")
    print(f"  payments:    {len(payments):,}")
    print(f"  reviews:     {len(reviews):,}")

    db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ecommerce.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    write_to_sqlite(customers, orders, order_items, payments, reviews, db_path)
    print(f"\nSQLite DB written to: {os.path.abspath(db_path)}")
