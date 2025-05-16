"""mgerp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from dashboard import views as dashboard_views


urlpatterns = [
    path('', lambda request: redirect('login')),  # Redirect empty path to login
    path('admin/', admin.site.urls),
    # Use the custom template from the registration app
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
    # Placeholder URL includes for additional apps (create these apps later)
    path('sales/', include('sales.urls')),
    path('accounting/', include('accounting.urls')),
    path('contacts/', include('contacts.urls')),
    path('salaries/', include('salaries.urls')),
    path('spareparts/', include('spare_parts.urls', namespace='spare_parts')),
]
