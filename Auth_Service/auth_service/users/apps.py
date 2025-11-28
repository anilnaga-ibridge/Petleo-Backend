# from django.apps import AppConfig


# class UsersConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'users'
# users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    # def ready(self):
    #     # ✅ Import inside ready(), after Django is initialized
    #     try:
    #         from super_admin.kafka_consumer import start_consumer_thread
    #         import threading
    #         thread = threading.Thread(target=start_consumer_thread, daemon=True)
    #         thread.start()
    #     except Exception as e:
    #         print(f"[UsersConfig] Kafka consumer not started: {e}")
