# oraw_app/views.py
from __future__ import annotations

# ============================================================================
# IMPORTS / TUONNIT
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView

from oraw_app.models import (
    Competition,
    Athlete,
    Result,
    Course,
    Split,
)
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list


# ============================================================================
# HOME VIEW / ETUSIVU
# ============================================================================
def home(request):
    """
    FI: Etusivu (staattinen placeholder).
    EN: Home page (static placeholder).
    """
    return render(request, "oraw_app/home.html")


# ============================================================================
# IOFXML UPLOAD (STAFF ONLY)
# ============================================================================
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    FI: Sallii vain staff-käyttäjät.
    EN: Allows only staff users.
    """

    def test_func(self):
        user = self.request.user
        return bool(user and user.is_staff)


class IOFXMLUploadView(StaffRequiredMixin, FormView):
    """
    FI: IOFXML 3.0 ResultList -tiedoston lataus ja tuonti (vain staff).
    EN: IOFXML 3.0 ResultList upload & import (staff only).
    """

    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]
        xml_bytes = uploaded_file.read()

        report = import_iofxml_result_list(
            xml_bytes,
            filename=uploaded_file.name,
            uploaded_by=self.request.user,
        )

        # Kaksikielinen viesti
        msg_fi = (
            "IOFXML-tuonti valmis. "
            f"Kilpailuja luotu: {report.competitions_created}, päivitetty: {report.competitions_updated}. "
            f"Ratoja luotu: {report.courses_created}. "
            f"Urheilijoita luotu: {report.athletes_created}. "
            f"Tuloksia luotu: {report.results_created}, päivitetty: {report.results_updated}. "
            f"Väliaikoja luotu: {report.splits_created}."
        )
        msg_en = (
            "IOFXML import completed. "
            f"Competitions created: {report.competitions_created}, updated: {report.competitions_updated}. "
            f"Courses created: {report.courses_created}. "
            f"Athletes created: {report.athletes_created}. "
            f"Results created: {report.results_created}, updated: {report.results_updated}. "
            f"Splits created: {report.splits_created}."
        )

        messages.success(self.request, msg_fi + " / " + msg_en)
        return super().form_valid(form)


# ============================================================================
# COMPETITIONS: LIST + DETAIL + COURSE RESULTS
# ============================================================================
class CompetitionListView(ListView):
    """
    FI: Listaa kaikki kilpailut aikajärjestyksessä (uusin ensin).
    EN: List competitions ordered by date (newest first).
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    ordering = ["-date"]


class CompetitionDetailView(DetailView):
    """
    FI: Näyttää yhden kilpailun perustiedot ja radat.
    EN: Displays one competition and its courses.
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["courses"] = Course.objects.filter(competition=self.object).order_by("name")
        return ctx


class CourseResultsView(ListView):
    """
    FI: Näyttää yhden radan kaikki tulokset.
    EN: Shows all results for a single course.
    """

    model = Result
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "results"

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        course_id = self.kwargs["course_id"]

        self.course = Course.objects.select_related("competition").get(
            id=course_id,
            competition__id=competition_id,
        )

        return (
            Result.objects.filter(
                course=self.course,
                is_public=True,
                deleted_at__isnull=True,
            )
            .select_related("athlete", "course__competition", "control_card")
            .order_by("position", "finish_time_s")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["course"] = self.course
        ctx["competition"] = self.course.competition
        return ctx


# ============================================================================
# RESULTS: DETAIL (SPLIT TIMES)
# ============================================================================
class ResultDetailView(DetailView):
    """
    FI: Näyttää yhden tuloksen tiedot ja väliajat.
    EN: Displays a result and its split times.
    """

    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        result: Result = self.object
        ctx["competition"] = result.course.competition
        ctx["course"] = result.course
        ctx["athlete"] = result.athlete
        ctx["splits"] = Split.objects.filter(result=result).order_by("seq")

        return ctx


# ============================================================================
# ATHLETES: LIST + DETAIL
# ============================================================================
class AthleteListView(ListView):
    """
    FI: Urheilijalista hakutoiminnoilla.
    EN: Athlete list with search filters.
    """

    model = Athlete
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        club = (self.request.GET.get("club") or "").strip()
        gender = (self.request.GET.get("gender") or "").strip()

        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(public_alias__icontains=q))
        if club:
            qs = qs.filter(club__icontains=club)
        if gender:
            qs = qs.filter(gender=gender)

        return qs.order_by("full_name")


class AthleteDetailView(DetailView):
    """
    FI: Näyttää urheilijan ja hänen tuloshistoriansa.
    EN: Displays an athlete and their result history.
    """

    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        athlete = self.object

        ctx["results"] = (
            Result.objects.filter(athlete=athlete)
            .select_related("course__competition")
            .order_by("-course__competition__date", "course__name")
        )

        return ctx


# ============================================================================
# SIGNUP + LOGOUT
# ============================================================================
class SignUpView(FormView):
    """
    FI: Rekisteröinti omalla SignupFormilla.
    EN: Registration view using SignupForm.
    """

    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """
    FI: Uloskirjautuminen POST-metodilla + viesti.
    EN: Logout with POST + message.
    """

    next_page = "oraw_app:home"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "Olet kirjautunut ulos.")
        return response
