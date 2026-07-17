import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "capstone.db"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        price REAL,
        imageUrl TEXT,
        rating REAL,
        category TEXT
    )
    """)
    
    # Create purchases table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        invoice_no TEXT,
        customer_id INTEGER,
        product_id TEXT,
        price REAL,
        quantity INTEGER,
        timestamp TEXT,
        PRIMARY KEY (invoice_no, product_id)
    )
    """)
    
    conn.commit()
    conn.close()

def populate_products_if_empty(products: list[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count == 0:
        for p in products:
            cursor.execute("""
            INSERT OR IGNORE INTO products (id, name, description, price, imageUrl, rating, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p["description"], p["price"], p["imageUrl"], p["rating"], p["category"]))
        conn.commit()
    conn.close()
