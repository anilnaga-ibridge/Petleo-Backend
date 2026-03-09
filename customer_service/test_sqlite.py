import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT id, price_snapshot, created_at FROM carts_cartitem ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    print("Latest 5 Cart Items in DB:")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print(f"Error: {e}")

