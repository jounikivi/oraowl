# oraw_app/urls.py
"""
FI: ORAOwl-sovelluksen URL-reitit.
    Tämä tiedosto määrittelee sovelluksen pääreitit:
    - Etusivu, IOFXML-tuonti, kilpailut ja urheilijat
    - Käyttäjäautentikointi (kirjautuminen, rekisteröinti, salasanan palautus)

EN: URL configuration for the ORAOwl application.
    Defines all main routes:
    - Home, IOFXML import, competitions, and athletes
    - Authentication (login, signup, password reset)
"""

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView, LogoutView
from . import views


# ============================================================================
# Namespace for templates / Namespace templatelle
# ============================================================================
app_name = "oraw_app"


# ============================================================================
# Main URL patterns / Sovelluksen reitit
# ============================================================================
urlpatterns = [
    # ------------------------------------------------------------------------
    # Home / Etusivu
    # ------------------------------------------------------------------------
    path("", views.home, name="home"),

    # ------------------------------------------------------------------------
    # IOFXML upload / IOFXML-tiedoston lataus
    # ------------------------------------------------------------------------
    path("upload/iofxml/", views.UploadIOFXMLView.as_view(), name="upload_iofxml"),

    # ------------------------------------------------------------------------
    # Competitions / Kilpailut
    # ------------------------------------------------------------------------
    path(
        "competitions/",
        views.CompetitionListView.as_view(),
        name="competitions_index",
    ),
    path(
        "competitions/<uuid:pk>/",
        views.CompetitionDetailView.as_view(),
        name="competitions_detail",
    ),

    # ------------------------------------------------------------------------
    # Athletes / Urheilijat
    # ------------------------------------------------------------------------
    path("athletes/", views.AthleteListView.as_view(), name="athletes_index"),
    path(
        "athletes/<uuid:pk>/",
        views.AthleteDetailView.as_view(),
        name="athletes_detail",
    ),

    # ------------------------------------------------------------------------
    # Authentication: login / logout / signup
    # ------------------------------------------------------------------------
    path(
        "accounts/login/",
        LoginView.as_view(template_name="oraw_app/accounts/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        LogoutView.as_view(next_page="oraw_app:home"),
        name="logout",
    ),
    path(
        "accounts/signup/",
        views.SignUpView.as_view(),
        name="signup",
    ),

    # ------------------------------------------------------------------------
    # Password reset (4 secure steps) / Salasanan palautus (4 vaihetta)
    # ------------------------------------------------------------------------
    path(
        "accounts/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="oraw_app/accounts/password_reset_form.html",
            email_template_name="oraw_app/accounts/password_reset_email.txt",
            subject_template_name="oraw_app/accounts/password_reset_subject.txt",
            success_url=reverse_lazy("oraw_app:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "accounts/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="oraw_app/accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="oraw_app/accounts/password_reset_confirm.html",
            success_url=reverse_lazy("oraw_app:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="oraw_app/accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    
    path(
    "accounts/logout/",
    LogoutView.as_view(next_page="oraw_app:home"),
    name="logout",
    ),
]
# ============================================================================#