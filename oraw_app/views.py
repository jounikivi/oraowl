# oraw_app/views.py

# ============================================================================
# Imports / Tuonnit
# ============================================================================

from django.contrib import messages
from django.db.models import Q, Min, Max
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LogoutView
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    FormView,
    TemplateView,
)

from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.models import Competition, Athlete, Result, Course, Split
from oraw_app.utils.iofxml_importer import import_iofxml_result_list

User = get_user_model()


# ============================================================================
# Home view / Etusivu
# ============================================================================


class HomeView(TemplateView):
    """
    FI: Yksinkertainen etusivu.
    EN: Simple home page.
    """

    template_name = "oraw_app/home.html"


# ============================================================================
# Competition list & detail views / Kilpailunäkymät
# ============================================================================


class CompetitionListView(ListView):
    """
    FI: Julkisten kilpailujen listaus.
    EN: List public competitions.
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Competition.objects.filter(is_public=True, deleted_at__isnull=True)
            .order_by("-date", "name")
            .select_related()
        )

        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(city__icontains=search)
                | Q(organiser__icontains=search)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        return ctx


class CompetitionDetailView(DetailView):
    """
    FI: Yhden kilpailun näkymä.
    EN: Single competition view.
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_queryset(self):
        return Competition.objects.filter(is_public=True, deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        competition = self.object

        # Haetaan kurssit/radat tälle kilpailulle
        courses = Course.objects.filter(
            competition=competition, is_public=True, deleted_at__isnull=True
        ).order_by("name")

        # Tulosten määrät per rata
        course_stats = (
            Result.objects.filter(
                course__competition=competition,
                is_public=True,
                deleted_at__isnull=True,
            )
            .values("course")
            .order_by("course")
            .annotate(total_results_count=Q("course"))
        )

        # Tehdään helppo dict course_id -> stats
        stats_by_course = {row["course"]: row["total_results_count"] for row in course_stats}

        ctx["courses"] = courses
        ctx["stats_by_course"] = stats_by_course
        return ctx


class CourseResultsView(ListView):
    """
    FI: Yhden radan tuloslista.
    EN: Results for a single course.
    """

    model = Result
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "results"

    def get_queryset(self):
        competition_id = self.kwargs.get("competition_id")
        course_id = self.kwargs.get("course_id")

        # Varmistetaan, että kilpailu ja rata ovat julkisia ja olemassa
        try:
            self.competition = Competition.objects.get(
                pk=competition_id, is_public=True, deleted_at__isnull=True
            )
        except Competition.DoesNotExist:
            raise Http404("Competition not found")

        try:
            self.course = Course.objects.get(
                pk=course_id,
                competition=self.competition,
                is_public=True,
                deleted_at__isnull=True,
            )
        except Course.DoesNotExist:
            raise Http404("Course not found")

        qs = (
            Result.objects.filter(
                course=self.course,
                is_public=True,
                deleted_at__isnull=True,
            )
            .select_related("athlete", "course__competition")
            .order_by("position", "finish_time_s", "bib")
        )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["competition"] = self.competition
        ctx["course"] = self.course
        return ctx


class ResultDetailView(DetailView):
    """
    FI: Yhden tuloksen ja väliaikojen näkymä.
    EN: Single result + splits.
    """

    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_queryset(self):
        return Result.objects.filter(
            is_public=True,
            deleted_at__isnull=True,
        ).select_related(
            "athlete",
            "course__competition",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        result = self.object
        course = result.course
        competition = course.competition
        athlete = result.athlete

        splits = Split.objects.filter(result=result).order_by("seq")

        ctx["competition"] = competition
        ctx["course"] = course
        ctx["athlete"] = athlete
        ctx["splits"] = splits
        return ctx


# ============================================================================
# Athlete list & detail views / Urheilijanäkymät
# ============================================================================


class AthleteListView(ListView):
    """
    FI: Urheilijalistaus.
    EN: Athletes index page.
    """

    model = Athlete
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    paginate_by = 50

    def get_queryset(self):
        qs = Athlete.objects.filter(
            is_public=True,
            deleted_at__isnull=True,
        ).order_by("last_name", "first_name")

        search = self.request.GET.get("q", "").strip()
        club = self.request.GET.get("club", "").strip()

        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(nickname__icontains=search)
            )

        if club:
            qs = qs.filter(club__icontains=club)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["club_query"] = self.request.GET.get("club", "").strip()
        return ctx


class AthleteDetailView(DetailView):
    """
    FI: Yksittäisen urheilijan profiilisivu + kilpailuhistoria.
    EN: Single athlete profile page + competition history.
    """

    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_queryset(self):
        return Athlete.objects.filter(
            is_public=True,
            deleted_at__isnull=True,
        )

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

        if results_qs.exists():
            best_result = ok_results_qs.order_by("position").first()
            best_position = best_result.position if best_result and best_result.position else None

            date_range = results_qs.aggregate(
                first_date=Min("course__competition__date"),
                latest_date=Max("course__competition__date"),
            )
            latest_date = date_range["latest_date"]
        else:
            best_position = None
            latest_date = None

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
# IOF XML upload / IOFXML-tuonti
# ============================================================================


class IOFXMLUploadView(PermissionRequiredMixin, FormView):
    """
    FI: IOF XML 3.0 tuloslistan tuonti.
    EN: Import IOF XML 3.0 result list.
    """

    template_name = "oraw_app/iofxml_upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")
    permission_required = "oraw_app.can_import_results"

    def form_valid(self, form):
        xml_file = form.cleaned_data["xml_file"]

        try:
            imported_competition = import_iofxml_result_list(xml_file)
        except Exception as exc:  # noqa: BLE001
            messages.error(self.request, f"Tiedoston tuonti epäonnistui: {exc}")
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Tiedoston tuonti onnistui. Kilpailu: {imported_competition}",
        )
        return super().form_valid(form)


# ============================================================================
# Signup / Login / Logout
# ============================================================================


class SignupView(FormView):
    """
    FI: Uuden käyttäjän rekisteröinti.
    EN: User signup view.
    """

    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Tervetuloa ORAOwl-palveluun!")
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
