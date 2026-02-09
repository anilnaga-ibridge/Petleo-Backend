import psycopg2

def check_auth_user():
    conn = psycopg2.connect(
        dbname="Auth_Service",
        user="petleo",
        password="petleo",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    cur.execute("SELECT id, phone_number FROM users_user WHERE id = 'f0be4128-b779-4f78-b2ab-48fcb5a5bab1';")
    row = cur.fetchone()
    if row:
        print(f"ID: {row[0]}")
        print(f"Phone Number: {row[1]}")
    else:
        print("User not found in Auth_Service")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_auth_user()
