import logging
from .models import OrganizationEmployee, VerifiedUser

logger = logging.getLogger(__name__)

class RBACMiddleware:
    """
    Enterprise middleware to resolve and attach capabilities to the request.
    This fulfills the "Centralized Permission Resolver" requirement.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # 1. Resolve effective capabilities (using versioned cache per logic in models.py)
                auth_id = getattr(request.user, 'auth_user_id', None)
                if auth_id:
                    # Check if employee or provider
                    emp = OrganizationEmployee.objects.filter(auth_user_id=auth_id).first()
                    if emp:
                        request.capabilities = set(emp.get_final_permissions())
                    else:
                        vu = VerifiedUser.objects.filter(auth_user_id=auth_id).first()
                        if vu:
                            request.capabilities = vu.get_all_plan_capabilities()
                        else:
                            request.capabilities = set()
                else:
                    request.capabilities = set()
                    
            except Exception as e:
                logger.error(f"RBAC Middleware Error: {e}")
                request.capabilities = set()
        else:
            request.capabilities = set()

        response = self.get_response(request)
        return response
