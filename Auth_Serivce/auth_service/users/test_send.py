from kafka_producer import publish_user_created_event

# Example user data
user_data = {
    "user_id": 1,
    "username": "Anil",
    "email": "anil@example.com",
    "phone": "9876543210",
    "token": "test-jwt-token"
}

# Publish the event
publish_user_created_event(user_data)

print("✅ User event sent to Kafka!")
