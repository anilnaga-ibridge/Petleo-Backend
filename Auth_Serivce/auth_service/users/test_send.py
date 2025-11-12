from kafka_producer import publish_user_created_event
def publish_user_created_event(user_data):
    role_value = user_data.get("role") or getattr(user_data, "role", None)
    if not role_value:
        logger.error(f"❌ Missing role in user_data: {user_data}")
        return

    event_data = {
        "auth_user_id": str(user_data.get("id")),
        "full_name": user_data.get("full_name"),
        "email": user_data.get("email"),
        "phone_number": user_data.get("phone_number"),
        "role": role_value,   # ✅ Always filled
    }
    publish_event("USER_CREATED", event_data)
