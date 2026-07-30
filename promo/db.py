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
    _run_migrations(conn)
    conn.commit()
    conn.close()


def _run_migrations(conn):
    """Migrações leves: adicionam colunas de versões mais novas do app em
    bancos criados antes delas existirem, sem apagar nada que já estava
    salvo."""
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(products)").fetchall()]

    if "external_id" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN external_id TEXT")
    if "brand" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN brand TEXT")
    if "image_url" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN image_url TEXT")
    if "shop_id" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN shop_id TEXT")
    if "liked" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN liked INTEGER NOT NULL DEFAULT 0")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_external
        ON products(platform, external_id)
        WHERE external_id IS NOT NULL
        """
    )


def insert_product(product: dict) -> int:
    product = {"brand": None, "image_url": None, "shop_id": None, **product}
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO products
            (name, category, platform, store_name, original_price, promo_price,
             commission_rate, commission, link, coupon, extra_details, status,
             brand, image_url)
        VALUES (:name, :category, :platform, :store_name, :original_price, :promo_price,
                :commission_rate, :commission, :link, :coupon, :extra_details, :status,
                :brand, :image_url)
        """,
        product,
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def upsert_shopee_product(product: dict) -> bool:
    """Insere um produto vindo da busca de ofertas da Shopee, ou atualiza
    preço/comissão/link se um produto com o mesmo external_id já existir.

    Não sobrescreve a categoria nem o status de produtos já existentes (você
    pode já ter ajustado a categoria manualmente ou marcado como enviado).
    Retorna True se foi um produto novo, False se foi uma atualização.
    """
    product = {"brand": None, "image_url": None, "shop_id": None, **product}
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM products WHERE platform = ? AND external_id = ?",
        (product["platform"], product["external_id"]),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE products
            SET name = :name, store_name = :store_name, promo_price = :promo_price,
                commission_rate = :commission_rate, commission = :commission, link = :link,
                image_url = :image_url, shop_id = :shop_id,
                brand = COALESCE(brand, :brand)
            WHERE id = :id
            """,
            {**product, "id": existing["id"]},
        )
        conn.commit()
        conn.close()
        return False

    conn.execute(
        """
        INSERT INTO products
            (name, category, platform, store_name, original_price, promo_price,
             commission_rate, commission, link, coupon, extra_details, status, external_id,
             brand, image_url, shop_id)
        VALUES (:name, :category, :platform, :store_name, :original_price, :promo_price,
                :commission_rate, :commission, :link, :coupon, :extra_details, :status, :external_id,
                :brand, :image_url, :shop_id)
        """,
        product,
    )
    conn.commit()
    conn.close()
    return True


def toggle_liked(product_id: int) -> bool:
    """Alterna a marcação de "bom exemplo" de um produto. Retorna o novo
    valor (True = marcado)."""
    conn = get_connection()
    row = conn.execute("SELECT liked FROM products WHERE id = ?", (product_id,)).fetchone()
    new_value = 0 if row and row["liked"] else 1
    conn.execute("UPDATE products SET liked = ? WHERE id = ?", (new_value, product_id))
    conn.commit()
    conn.close()
    return bool(new_value)


def get_liked_shopee_shop_ids() -> list:
    """IDs de loja (shop_id) de produtos da Shopee marcados como "bom
    exemplo" - usados para buscar mais ofertas dessas mesmas lojas."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT shop_id FROM products
        WHERE platform = 'Shopee' AND liked = 1 AND shop_id IS NOT NULL
        """
    ).fetchall()
    conn.close()
    return [row["shop_id"] for row in rows]


def list_products(category: str = None, status: str = None, liked_only: bool = False):
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    if liked_only:
        query += " AND liked = 1"
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


def delete_all_products() -> int:
    """Apaga todos os produtos da lista, de qualquer origem. Retorna quantos
    foram removidos."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    conn.execute("DELETE FROM products")
    conn.commit()
    conn.close()
    return count
