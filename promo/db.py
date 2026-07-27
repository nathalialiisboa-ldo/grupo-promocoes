import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

STATUS_PENDENTE = "pendente"
STATUS_ENVIADO = "enviado"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            platform TEXT,
            store_name TEXT,
            original_price REAL,
            promo_price REAL NOT NULL,
            commission_rate TEXT,
            commission TEXT,
            link TEXT NOT NULL,
            coupon TEXT,
            extra_details TEXT,
            status TEXT NOT NULL DEFAULT 'pendente',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def insert_product(product: dict) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO products
            (name, category, platform, store_name, original_price, promo_price,
             commission_rate, commission, link, coupon, extra_details, status)
        VALUES (:name, :category, :platform, :store_name, :original_price, :promo_price,
                :commission_rate, :commission, :link, :coupon, :extra_details, :status)
        """,
        product,
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_products(category: str = None, status: str = None):
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC, id DESC"
    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_product(product_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def update_status(product_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE products SET status = ? WHERE id = ?", (status, product_id))
    conn.commit()
    conn.close()


def update_category(product_id: int, category: str):
    conn = get_connection()
    conn.execute("UPDATE products SET category = ? WHERE id = ?", (category, product_id))
    conn.commit()
    conn.close()


def delete_product(product_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
