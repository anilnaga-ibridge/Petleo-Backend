# service_provider/permissions.py

from rest_framework.permissions import BasePermission
from service_provider.models import LocalProviderPermission


def user_has_local_permission(auth_user_id, service_id, category_id, action):
    try:
        perm = LocalProviderPermission.objects.get(
            auth_user_id=auth_user_id,
            service_id=service_id,
            category_id=category_id,
        )
        return getattr(perm, f"can_{action}", False)
    except LocalProviderPermission.DoesNotExist:
        return False


class HasServicePermission(BasePermission):
    """
    DRF Permission Class
    """

    def has_permission(self, request, view):
        auth_user_id = request.user.id

        service_id = view.kwargs.get("service_id")
        category_id = view.kwargs.get("category_id")

        action_map = {
            "GET": "view",
            "POST": "create",
            "PUT": "edit",
            "PATCH": "edit",
            "DELETE": "delete",
        }

        action = action_map.get(request.method)

        return user_has_local_permission(auth_user_id, service_id, category_id, action)
