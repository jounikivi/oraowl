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
    FI: Urheilijalista taulukkona, tukee hakua ja suodatuksia (?q, ?club, ?gender).
    EN: Athlete list with filters (?q, ?club, ?gender).
    """
    model = Athlete
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    paginate_by = 25

    def get_queryset(self):
        """
        FI:
            Rakentaa hakuehdot ja palauttaa järjestetyn tuloksen.
            Haetaan vain julkiset ja ei-poistetut urheilijat.
        EN:
            Builds search filters and returns an ordered queryset.
            Only public and non-deleted athletes are included.
        """
        qs = super().get_queryset().filter(
            is_public=True,
            deleted_at__isnull=True,
        )

        q = (self.request.GET.get("q") or "").strip()
        club = (self.request.GET.get("club") or "").strip()
        gender = (self.request.GET.get("gender") or "").strip()

        if q:
            # FI: Hae etu- ja sukunimestä sekä mahdollisesta public_aliasista
            # EN: Search first name, last name and optional public_alias
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(public_alias__icontains=q)
            )

        if club:
            qs = qs.filter(club__icontains=club)

        if gender:
            qs = qs.filter(gender=gender)

        # FI: Järjestys: sukunimi, etunimi, alias
        # EN: Order: last name, first name, alias
        return qs.order_by("last_name", "first_name", "public_alias")


class AthleteDetailView(DetailView):
    """
    FI:
        Näyttää urheilijan profiilisivun sekä kilpailuhistorian.
        Lisäksi lasketaan pieni yhteenveto tilastoista:
        - kilpailujen määrä
        - tulosten määrä
        - OK-tulosten määrä
        - podium-sijoitukset (1–3)
        - paras sijoitus
        - viimeisin kilpailupäivä

    EN:
        Displays the athlete profile and competition history.
        Also provides a small stats summary:
        - number of competitions
        - number of results
        - number of OK results
        - podium finishes (1–3)
        - best position
        - date of latest competition
    """

    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        athlete = self.object

        # ------------------------------------------------------------
        # FI: Haetaan urheilijan julkiset tulokset
        # EN: Fetch public (non-deleted) results for this athlete
        # ------------------------------------------------------------
        results_qs = (
            Result.objects.filter(
                athlete=athlete,
                is_public=True,
                deleted_at__isnull=True,
            )
            .select_related("course__competition")
            .order_by("-course__competition__date", "course__name")
        )

        ctx["results"] = results_qs

        # ------------------------------------------------------------
        # FI: Lasketaan yhteenvedon tilastot
        # EN: Compute summary statistics
        # ------------------------------------------------------------
        total_results = results_qs.count()
        competitions_count = (
            results_qs.values("course__competition").distinct().count()
            if total_results
            else 0
        )

        ok_results_qs = results_qs.filter(status="OK")
        ok_results = ok_results_qs.count()
        podiums = ok_results_qs.filter(position__in=[1, 2, 3]).count()

        best_position_obj = (
            ok_results_qs.exclude(position__isnull=True).order_by("position").first()
        )
        best_position = best_position_obj.position if best_position_obj else None

        latest_result = results_qs.first()
        latest_date = (
            latest_result.course.competition.date if latest_result else None
        )

        ctx["stats"] = {
            "total_results": total_results,
            "competitions_count": competitions_count,
            "ok_results": ok_results,
            "podiums": podiums,
            "best_position": best_position,
            "latest_date": latest_date,
        }

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
