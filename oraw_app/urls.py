"""
FI: ORAOwl-sovelluksen URL-reitit (suomenkieliset ja siistit polut).
EN: ORAOwl URL routes (clean, Finnish-friendly paths).
"""

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView
from . import views 


app_name = "oraw_app"

urlpatterns = [
    # ------------------------------------------------------------------------
    # Etusivu
    # ------------------------------------------------------------------------
    path("", HomeView.as_view(), name="home"),


    # ------------------------------------------------------------------------
    # IOFXML-tuonti
    # ------------------------------------------------------------------------
    path(
        "tuonti/iofxml/",
        views.IOFXMLUploadView.as_view(),
        name="iofxml_upload",
    ),

    # ------------------------------------------------------------------------
    # Kilpailut / Competitions
    # ------------------------------------------------------------------------
    # Kilpailulista: /kilpailut/
    path(
        "kilpailut/",
        views.CompetitionListView.as_view(),
        name="competition_list",
    ),

    # Kilpailun perusnäkymä: /kilpailut/<kilpailu_id>/
    path(
        "kilpailut/<uuid:pk>/",
        views.CompetitionDetailView.as_view(),
        name="competition_detail",
    ),

    # Radan tulossivu: /kilpailut/<kilpailu_id>/sarjat/<course_id>/
    path(
    "kilpailut/<uuid:competition_id>/sarjat/<uuid:course_id>/",
    views.CourseResultsView.as_view(),
    name="course_results",
    ),

    # Yksittäisen tulosrivin näkymä (jos tarvitset):
    path(
        "tulokset/<uuid:pk>/",
        views.ResultDetailView.as_view(),
        name="result_detail",
    ),

    # ------------------------------------------------------------------------
    # Urheilijat / Athletes
    # ------------------------------------------------------------------------
    path(
        "urheilijat/",
        views.AthleteListView.as_view(),
        name="athletes_index",
    ),
    path(
        "urheilijat/<uuid:pk>/",
        views.AthleteDetailView.as_view(),
        name="athletes_detail",
    ),

    # ------------------------------------------------------------------------
    # Tili / Käyttäjä (Login, Logout, Signup)
    # ------------------------------------------------------------------------
    path(
        "tili/kirjaudu/",
        LoginView.as_view(template_name="oraw_app/accounts/login.html"),
        name="login",
    ),
    path(
        "tili/ulos/",
        views.CustomLogoutView.as_view(),
        name="logout",
    ),
    path(
        "tili/rekisteroidy/",
        views.SignUpView.as_view(),
        name="signup",
    ),

    # ------------------------------------------------------------------------
    # Salasanan palautus
    # ------------------------------------------------------------------------
    path(
        "tili/salasana/palauta/",
        auth_views.PasswordResetView.as_view(
            template_name="oraw_app/accounts/password_reset_form.html",
            email_template_name="oraw_app/accounts/password_reset_email.txt",
            subject_template_name="oraw_app/accounts/password_reset_subject.txt",
            success_url=reverse_lazy("oraw_app:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "tili/salasana/palauta/valmis/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="oraw_app/accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "tili/salasana/uusi/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="oraw_app/accounts/password_reset_confirm.html",
            success_url=reverse_lazy("oraw_app:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "tili/salasana/uusi/valmis/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="oraw_app/accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # ------------------------------------------------------------------------
    # Salasanan vaihto
    # ------------------------------------------------------------------------
    path(
        "tili/salasana/vaihda/",
        auth_views.PasswordChangeView.as_view(
            template_name="oraw_app/accounts/password_change_form.html",
            success_url=reverse_lazy("oraw_app:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "tili/salasana/vaihda/valmis/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="oraw_app/accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),

    # ------------------------------------------------------------------------
    # Hallintapaneeli
    # ------------------------------------------------------------------------
    path(
        "hallinta/",
        views.AdminDashboardView.as_view(),
        name="admin_dashboard",
    ),
]
