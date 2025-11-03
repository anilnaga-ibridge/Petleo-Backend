"""
URL configuration for super_admin_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('superadmin/', include('admin_core.urls')),
    
    
    
    # Dynamic modules
    path("api/superadmin/", include("dynamic_services.urls")),
    path("api/superadmin/", include("dynamic_categories.urls")),
    path("api/superadmin/", include("dynamic_facilities.urls")),
    path("api/superadmin/", include("dynamic_pricing.urls")),
   

    # plans and copens
    path("api/superadmin/plans_coupens/", include("plans_coupens.urls")),
    
    # pets
      path('api/pets/', include('pets.urls')),
]
