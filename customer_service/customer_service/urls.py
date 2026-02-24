from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/customer/', include('customers.urls')),
    path('api/pet-owner/', include('customers.urls')),
    path('api/pet-owner/pets/', include('pets.urls')),
    path('api/pet-owner/bookings/', include('bookings.urls')),
    path('api/pet-owner/cart/', include('carts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
