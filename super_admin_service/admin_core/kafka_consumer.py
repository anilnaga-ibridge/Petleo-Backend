# # super_admin/kafka_consumer.py
# from kafka import KafkaConsumer
# import json
# import django
# import os

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")  # replace project_name
# django.setup()

# from admin_core.models import SuperAdmin


# consumer = KafkaConsumer(
#     'user_created',
#     bootstrap_servers='localhost:9092',
#     auto_offset_reset='earliest',
#     group_id='superadmin_group',
#     value_deserializer=lambda m: json.loads(m.decode('utf-8'))
# )

# print("SuperAdmin Service Kafka consumer started...")

# for message in consumer:
#     data = message.value
#     # Check if user already exists
#     if not SuperAdmin.objects.filter(auth_user_id=data["user_id"]).exists():
#         SuperAdmin.objects.create(
#             email=data["email"],
#             contact=data.get("contact", ""),
#             first_name=data.get("first_name", ""),
#             last_name=data.get("last_name", ""),
#             user_role=data.get("role", "superAdmin"),
#             auth_user_id=data["user_id"],
#             activity_status='active'
#         )
#         print(f"SuperAdmin created: {data['email']}")


# # super_admin/kafka_consumer.py
# from kafka import KafkaConsumer
# import json
# import os
# # import django

# # # Setup Django environment
# # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# # django.setup()

# # from admin_core.models import SuperAdmin

# # consumer = KafkaConsumer(
# #     'user_created',
# #     bootstrap_servers='localhost:9092',
# #     auto_offset_reset='earliest',
# #     group_id='superadmin_group',
# #     value_deserializer=lambda m: json.loads(m.decode('utf-8'))
# # )

# # print("SuperAdmin Service Kafka consumer started...")

# # for message in consumer:
# #     data = message.value

# #     # Use the correct key sent by the producer
# #     auth_user_id = data.get("auth_user_id")
# #     email = data.get("email")

# #     if not auth_user_id or not email:
# #         print("Skipping message: auth_user_id or email missing")
# #         continue

# #     # Avoid duplicates
# #     if SuperAdmin.objects.filter(auth_user_id=auth_user_id).exists():
# #         print(f"SuperAdmin already exists: {email}")
# #         continue

# #     extra = data.get("extra_fields", {})

# #     superadmin_data = {
# #         "auth_user_id": auth_user_id,
# #         "email": email,
# #         "first_name": extra.get("first_name", ""),
# #         "last_name": extra.get("last_name", ""),
# #         "contact": extra.get("contact", ""),
# #         "user_role": data.get("role", "superAdmin"),
# #         "is_active": True,
# #         "is_staff": True,
# #         "is_superuser": True,
# #         "is_super_admin": True,
# #         "activity_status": "active"
# #     }

# #     SuperAdmin.objects.create(**superadmin_data)
# #     print(f"SuperAdmin created: {email}")




# import json
# import os
# import django
# import logging
# from kafka import KafkaConsumer
# from django.db import IntegrityError, transaction

# # Django setup
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import SuperAdmin

# # Logging setup
# LOG_FILE = "kafka_consumer.log"
# logging.basicConfig(
#     filename=LOG_FILE,
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
# )

# # Kafka Consumer setup
# consumer = KafkaConsumer(
#     'superadmin-topic',        # Replace with your Kafka topic
#     bootstrap_servers=['localhost:9092'],  # Replace with your Kafka server
#     value_deserializer=lambda m: json.loads(m.decode('utf-8')),
#     auto_offset_reset='earliest',
#     enable_auto_commit=True
# )

# logging.info("SuperAdmin Service Kafka consumer started...")

# for message in consumer:
#     superadmin_data = message.value
#     email = superadmin_data.get("email")

#     if not email:
#         logging.warning("Skipping record: email is missing")
#         continue

#     try:
#         # Avoid duplicates using get_or_create
#         with transaction.atomic():
#             superadmin, created = SuperAdmin.objects.get_or_create(
#                 email=email,
#                 defaults=superadmin_data
#             )
#             if created:
#                 logging.info(f"SuperAdmin created: {email}")
#             else:
#                 logging.info(f"SuperAdmin already exists: {email}")

#     except IntegrityError as e:
#         logging.error(f"Database IntegrityError for {email}: {e}")
#     except Exception as e:
#         logging.error(f"Unexpected error for {email}: {e}")
