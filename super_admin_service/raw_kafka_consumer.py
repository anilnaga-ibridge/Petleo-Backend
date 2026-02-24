
import json
import logging
import time
import uuid
import psycopg2
from kafka import KafkaConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# DB Config
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "petleo"
DB_PASSWORD = "petleo"
DB_NAME = "Super_Admin"

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def normalize_role(role):
    if not role:
        return None
    return str(role).replace(" ", "").replace("_", "").lower()

def run_consumer():
    logger.info("🚀 Starting Raw SuperAdmin Kafka Consumer")
    
    consumer = None
    while not consumer:
        try:
            consumer = KafkaConsumer(
                "service_provider_events",
                "admin_events",
                "organization_events",
                "individual_events",
                bootstrap_servers="localhost:9093",
                group_id="superadmin-service-group-raw", # Adjusted group ID
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            logger.info("✅ Kafka Connected")
        except Exception as e:
            logger.warning(f"⚠️ Kafka unavailable: {e}")
            time.sleep(5)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        logger.info("✅ DB Connected")
    except Exception as e:
        logger.error(f"❌ DB Connection failed: {e}")
        return

    for message in consumer:
        try:
            # Re-connect DB if closed
            if conn.closed:
                conn = get_db_connection()
                cur = conn.cursor()

            event = message.value
            event_type = event.get("event_type", "").upper()
            data = event.get("data", {})
            raw_role = event.get("role")
            role = normalize_role(raw_role)
            auth_user_id = data.get("auth_user_id")

            logger.info(f"📨 EVENT: {event_type} | Role={role} | ID={auth_user_id}")
            
            if not auth_user_id:
                logger.warning("Skipping missing auth_user_id")
                continue

            if event_type in ["USER_CREATED", "ADMIN_CREATED", "SUPERADMIN_CREATED"]:
                # Upsert VerifiedUser
                # Check exist
                cur.execute("SELECT id FROM verified_users WHERE auth_user_id = %s", (str(auth_user_id),))
                exists = cur.fetchone()
                
                if exists:
                    # Update
                    cur.execute("""
                        UPDATE verified_users 
                        SET full_name=%s, email=%s, phone_number=%s, role=%s, avatar_url=%s, updated_at=NOW()
                        WHERE auth_user_id=%s
                    """, (data.get("full_name"), data.get("email"), data.get("phone_number"), role, data.get("avatar_url"), str(auth_user_id)))
                    logger.info(f"🔄 Updated VerifiedUser: {data.get('email')}")
                else:
                    # Insert
                    new_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO verified_users (id, auth_user_id, full_name, email, phone_number, role, avatar_url, permissions, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, '[]', NOW(), NOW())
                    """, (new_id, str(auth_user_id), data.get("full_name"), data.get("email"), data.get("phone_number"), role, data.get("avatar_url")))
                    logger.info(f"✅ Created VerifiedUser: {data.get('email')}")
                conn.commit()

            elif event_type in ["USER_UPDATED", "EMPLOYEE_UPDATED"]:
                cur.execute("""
                    UPDATE verified_users 
                    SET full_name=%s, email=%s, phone_number=%s, role=%s, avatar_url=%s, updated_at=NOW()
                    WHERE auth_user_id=%s
                """, (data.get("full_name"), data.get("email"), data.get("phone_number"), role, data.get("avatar_url"), str(auth_user_id)))
                conn.commit()
                logger.info(f"🆙 Updated VerifiedUser: {data.get('email')}")

            elif event_type in ["USER_DELETED", "ADMIN_DELETED", "SUPERADMIN_DELETED"]:
                # Delete Document first (FK constraint?)
                # Actually django usually handles FK, but here we manually delete or let cascade if DB has it
                # We assume manual deletion as per requirement
                cur.execute("DELETE FROM dynamic_fields_providerdocumentverification WHERE auth_user_id = %s", (str(auth_user_id),))
                doc_deleted = cur.rowcount
                
                cur.execute("DELETE FROM verified_users WHERE auth_user_id = %s", (str(auth_user_id),))
                user_deleted = cur.rowcount
                
                conn.commit()
                logger.info(f"🗑️ Deleted VerifiedUser ID={auth_user_id} ({user_deleted}) and Documents ({doc_deleted})")

            elif event_type == "PROVIDER.DOCUMENT.UPLOADED":
                doc_id = data.get("document_id")
                
                # Check if document exists
                cur.execute("SELECT id FROM dynamic_fields_providerdocumentverification WHERE document_id = %s", (str(doc_id),))
                doc_exists = cur.fetchone()

                # Determine status: if user is approved, pending, etc.
                # Simplified: default pending
                status = "pending"
                
                if doc_exists:
                    # Update
                     cur.execute("""
                        UPDATE dynamic_fields_providerdocumentverification
                        SET auth_user_id=%s, definition_id=%s, file_url=%s, filename=%s, status=%s, updated_at=NOW()
                        WHERE document_id=%s
                    """, (str(auth_user_id), data.get("definition_id"), data.get("file_url"), data.get("filename"), status, str(doc_id)))
                     logger.info(f"🔄 Updated Document: {data.get('filename')}")
                else:
                    # Insert
                    new_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO dynamic_fields_providerdocumentverification (id, document_id, auth_user_id, definition_id, file_url, filename, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (new_id, str(doc_id), str(auth_user_id), data.get("definition_id"), data.get("file_url"), data.get("filename"), status))
                    logger.info(f"✅ Created Document: {data.get('filename')}")
                
                conn.commit()

        except Exception as e:
            logger.exception(f"❌ Error processing message: {e}")
            if conn:
                conn.rollback()

if __name__ == "__main__":
    run_consumer()
