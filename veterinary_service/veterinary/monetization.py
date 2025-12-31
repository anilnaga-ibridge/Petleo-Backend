from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Feature Tiers
BASIC = 'BASIC'
PRO = 'PRO'
ENTERPRISE = 'ENTERPRISE'

def feature_tier(tier):
    """
    Decorator to tag endpoints with feature tiers.
    In the future, this will check the clinic's subscription plan.
    For now, it just logs the access.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            # Future: Check if request.user.clinic.subscription_tier >= tier
            logger.info(f"Accessing {tier} feature: {func.__name__} by User {request.user}")
            
            # For Phase 4, we allow access but log it.
            # if not has_tier_access(request.user, tier):
            #     raise PermissionDenied(f"Upgrade to {tier} to access this feature.")
            
            return func(view, request, *args, **kwargs)
        return wrapper
    return decorator
