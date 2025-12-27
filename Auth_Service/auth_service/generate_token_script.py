from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
try:
    user = User.objects.get(email='ram@gmail.com')
    refresh = RefreshToken.for_user(user)
    print(f"TOKEN_START:{str(refresh.access_token)}:TOKEN_END")
except User.DoesNotExist:
    print("User ram@gmail.com not found")
