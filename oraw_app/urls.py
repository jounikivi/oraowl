"""
URL configuration for oraowl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

from django.urls import path
#from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView, LoginView
from . import views

# FI: Namespace templatelle. 
# EN: URL namespace.
app_name = "oraw_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/iofxml/", views.UploadIOFXMLView.as_view(), name="upload_iofxml"),
    path("competitions/", views.CompetitionListView.as_view(), name="competitions_index"),
    path("competitions/<uuid:pk>/",views.CompetitionDetailView.as_view(),name="competitions_detail",
    ),
    path("athletes/", views.AthleteListView.as_view(), name="athletes_index"),
    path("athletes/<uuid:pk>/", views.AthleteDetailView.as_view(), name="athletes_detail"),
    
       # Login & Logout
    path(
        "accounts/login/",LoginView.as_view(template_name="oraw_app/accounts/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",LogoutView.as_view(next_page="oraw_app:home"),
        name="logout",
    ),

    # Signup (rekisteröinti) – toteutamme seuraavassa kohdassa SignUpView:n
    path("accounts/signup/", views.SignUpView.as_view(), name="signup"),
]

