import os
import psycopg2

def check_verified_users():
    conn = psycopg2.connect(
        dbname="Super_Admin",
        user="petleo",
        password="petleo",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    cur.execute("SELECT auth_user_id, full_name, email, phone_number, role FROM verified_users WHERE auth_user_id = 'f0be4128-b779-4f78-b2ab-48fcb5a5bab1';")
    row = cur.fetchone()
    if row:
        print(f"Auth User ID: {row[0]}")
        print(f"Full Name: {row[1]}")
        print(f"Email: {row[2]}")
        print(f"Phone Number: {row[3]}")
        print(f"Role: {row[4]}")
    else:
        print("User not found in verified_users")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_verified_users()
