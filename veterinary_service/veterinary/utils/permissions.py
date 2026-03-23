from functools import wraps
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('veterinary')

def permission_required(capability, action='view'):
    """
    RBAC Decorator for Veterinary Service.
    Checks granular permissions from the JWT permissions_summary.
    
    action values: 'view', 'create', 'edit', 'delete'
    """
    # Mapping long names to short keys used in Auth Service token generation
    ACTION_MAP = {
        'view': 'v',
        'create': 'c',
        'edit': 'e',
        'delete': 'd'
    }
    
    short_action = ACTION_MAP.get(action, 'v')

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(view_instance, request, *args, **kwargs):
            # 1. Ensure user is authenticated
            if not request.user or not request.user.is_authenticated:
                return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
            
            # 2. Get permissions summary from token
            summary = {}
            if request.auth:
                # Handle both dict-like and Token-object payloads
                auth_payload = {}
                if isinstance(request.auth, dict):
                    auth_payload = request.auth
                elif hasattr(request.auth, 'payload'):
                    auth_payload = request.auth.payload
                elif hasattr(request.auth, '__getitem__'):
                    # AccessToken/RefreshToken often behave like dicts
                    try:
                        # Some versions of SimpleJWT use this
                        auth_payload = request.auth
                    except:
                        pass
                
                if auth_payload:
                    summary = auth_payload.get('permissions_summary', {})
            
            # Support for legacy fallback if summary is empty (optional transition)
            if not summary:
                # If there's no summary in token, check the request.user.permissions list (legacy)
                
                # We'll translate our capability key to legacy enum if needed, 
                # but for new production-ready system, we expect the summary.
                legacy_perm = f"VETERINARY_{capability.split('.')[-1].upper()}"
                user_perms = getattr(request.user, 'permissions', [])
                
                # Direct match OR wildcard match (e.g. 'consultation.*' allows 'veterinary.consultation')
                module_wildcard = f"{capability.split('.')[0]}.*"
                if legacy_perm in user_perms or module_wildcard in user_perms:
                    return view_func(view_instance, request, *args, **kwargs)
                
                logger.warning(f"🚫 RBAC: User {request.user.username} lacks permissions_summary in token or legacy fallback.")
                return Response({"detail": f"Forbidden: Missing capability {capability}"}, status=status.HTTP_403_FORBIDDEN)

            # 3. Check granular capability
            cap_perms = summary.get(capability, {})
            if cap_perms.get(short_action):
                return view_func(view_instance, request, *args, **kwargs)
            
            logger.warning(f"🚫 RBAC: User {request.user.username} denied {action} on {capability}")
            return Response(
                {"detail": f"You do not have permission to {action} {capability.split('.')[-1]}."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return _wrapped_view
    return decorator
