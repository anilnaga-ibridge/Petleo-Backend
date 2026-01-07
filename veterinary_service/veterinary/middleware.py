import threading
from django.utils.deprecation import MiddlewareMixin
from .models import VeterinaryStaff

_thread_locals = threading.local()

def get_current_user_id():
    return getattr(_thread_locals, 'user_id', None)

class VeterinaryPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to attach VeterinaryStaff permissions to request.user.
    Also stores user_id in thread-local for signals.
    """
    def process_request(self, request):
        if not request.user or not request.user.is_authenticated:
            _thread_locals.user_id = None
            return

        try:
            auth_user_id = str(request.user.id)
            _thread_locals.user_id = auth_user_id
            
            # 2. Fetch VeterinaryStaff
            staff = VeterinaryStaff.objects.filter(auth_user_id=auth_user_id).first()
            
            if staff:
                # 3. Attach Permissions
                request.user.permissions = staff.permissions
                request.user.staff_profile = staff
                request.user.clinic_id = staff.clinic.id if staff.clinic else None
            else:
                request.user.permissions = []
                request.user.staff_profile = None
                request.user.clinic_id = None
                
        except Exception as e:
            print(f"Middleware Error: {e}")
            request.user.permissions = []
            _thread_locals.user_id = None

    def process_response(self, request, response):
        _thread_locals.user_id = None
        return response
