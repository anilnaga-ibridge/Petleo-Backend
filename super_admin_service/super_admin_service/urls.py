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
    path('api/superadmin/', include('admin_core.urls')),
    
    
    
    # Dynamic modules
    path("api/superadmin/", include("dynamic_services.urls")),
    path("api/superadmin/", include("dynamic_categories.urls")),
    path("api/superadmin/", include("dynamic_facilities.urls")),
    path("api/superadmin/", include("dynamic_pricing.urls")),
   

    # plans and copens
    path("api/superadmin/", include("plans_coupens.urls")),
    
    # pets
    path('api/superadmin/', include('pets.urls')),
      
      
      
      
    path("api/superadmin/provider-home/", include("provider_home.urls")),
      
    path("api/superadmin/", include("dynamic_fields.urls")),   # protected CRUD
    path("api/public/provider/", include("dynamic_fields.urls")), 
    
    path("api/superadmin/", include("dynamic_permissions.urls")), 
      
      

]
