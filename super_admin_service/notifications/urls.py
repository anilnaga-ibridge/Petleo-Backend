from django.urls import path
from .views import get_notifications, mark_read

urlpatterns = [
    path('<str:user_id>/', get_notifications, name='get_notifications'),
    path('read/<int:notification_id>/', mark_read, name='mark_read'),
]
