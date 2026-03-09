import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, consultation_fee, provider_id FROM service_provider_consultationtype LIMIT 5")
    rows = cursor.fetchall()
    print("Consultation Types in DB:")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
