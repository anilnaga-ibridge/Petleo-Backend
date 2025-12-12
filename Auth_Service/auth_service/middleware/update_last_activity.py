from django.utils import timezone

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = request.user
        if user.is_authenticated:
            # If the user was deleted during the request (e.g. DELETE /users/id/),
            # saving will fail. We catch this to avoid 500 errors.
            try:
                user.last_active_at = timezone.now()
                user.save(update_fields=["last_active_at"])
            except Exception:
                pass

        return response
