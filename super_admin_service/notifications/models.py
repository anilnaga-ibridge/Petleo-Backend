from django.db import models

class Notification(models.Model):
    user_id = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} - {self.user_id}'
