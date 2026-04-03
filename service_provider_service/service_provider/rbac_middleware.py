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
                # 1. Resolve auth_user_id
                # request.user is often a VerifiedUser instance from VerifiedUserJWTAuthentication
                auth_id = getattr(request.user, 'auth_user_id', None)
                
                if auth_id:
                    # 2. Check for Employee context first (employees have restricted subsets of plan)
                    emp = OrganizationEmployee.objects.filter(auth_user_id=auth_id).first()
                    if emp:
                        request.capabilities = set(emp.get_final_permissions())
                        print(f"🔐 [RBAC] Employee Context: {request.user.email} | Caps: {len(request.capabilities)}")
                    else:
                        # 3. Owner context (Organization/Individual/Super Admin)
                        # If authenticated as VerifiedUser, we use its plan capabilities
                        if hasattr(request.user, 'get_all_plan_capabilities'):
                            request.capabilities = request.user.get_all_plan_capabilities()
                            print(f"🔐 [RBAC] Owner Context: {request.user.email} | Caps: {len(request.capabilities)}")
                        else:
                            # Fallback: re-fetch from DB if request.user is a standard Django User
                            vu = VerifiedUser.objects.filter(auth_user_id=auth_id).first()
                            if vu:
                                request.capabilities = vu.get_all_plan_capabilities()
                                print(f"🔐 [RBAC] Resolved Owner from DB: {request.user.email}")
                            else:
                                request.capabilities = set()
                                print(f"⚠️ [RBAC] No VerifiedUser record for {request.user.email}")
                else:
                    request.capabilities = set()
                    print(f"⚠️ [RBAC] auth_user_id missing on request.user")
                    
            except Exception as e:
                logger.error(f"RBAC Middleware Error: {e}")
                request.capabilities = set()
                print(f"❌ [RBAC] Middleware Error: {e}")
                    
            except Exception as e:
                logger.error(f"RBAC Middleware Error: {e}")
                request.capabilities = set()
        else:
            request.capabilities = set()

        response = self.get_response(request)
        return response
