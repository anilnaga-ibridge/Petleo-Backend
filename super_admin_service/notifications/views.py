from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Notification

def get_notifications(request, user_id):
    limit = int(request.GET.get("limit", 20))
    notifs = Notification.objects.filter(user_id=user_id).order_by("-created_at")[:limit]
    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        }
        for n in notifs
    ]
    return JsonResponse(data, safe=False)

@csrf_exempt
def mark_read(request, notification_id):
    try:
        notif = Notification.objects.get(id=notification_id)
        notif.is_read = True
        notif.save()
        return JsonResponse({"status": "success"})
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
