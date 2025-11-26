# oraw_app/views.py

# ============================================================================
# Imports / Tuonnit
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    FormView,
    TemplateView,
    CreateView,
)
from django.contrib.auth import login, get_user_model
from django.contrib.auth.views import LogoutView
from django.http import Http404

from oraw_app.models import Competition, Athlete, Result, Course, Split
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list

User = get_user_model()


# ============================================================================
# Perusnäkymät / Basic views
# ============================================================================


def home(request):
    """
    FI:
        Etusivu. Täällä voidaan näyttää esim. lyhyt kuvaus ORAOwlista
        ja muutama nosto kilpailuista.
    EN:
        Home page. You can later add small statistics or a description here.
    """
    return render(request, "oraw_app/home.html")


# ============================================================================
# Staff mixin (vain henkilöstölle) / Staff-only mixin
# ============================================================================


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    FI:
        Mixin, joka varmistaa että käyttäjä on kirjautunut ja on staff (is_staff=True).
    EN:
        Mixin that ensures the user is authenticated and marked as staff.
    """

    def test_func(self):
        user = self.request.user
        return bool(user and user.is_staff)


# ============================================================================
# IOFXML upload view / IOFXML-latausnäkymä
# ============================================================================


class IOFXMLUploadView(StaffRequiredMixin, FormView):
    """
    FI:
        IOFXML 3.0 ResultList -tiedoston lataus- ja tuontinäkymä (vain staff).
    EN:
        IOFXML 3.0 ResultList upload & import view (staff only).
    """

    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    def form_valid(self, form):
        """
        FI:
            Kun lomake on validi, luetaan XML-tiedosto, ajetaan importer ja
            näytetään käyttäjälle yhteenveto tuonnista.
        EN:
            When the form is valid, read the XML file, run the importer and
            show a summary message to the user.
        """
        uploaded_file = form.cleaned_data["file"]
        xml_bytes = uploaded_file.read()

        report = import_iofxml_result_list(
            xml_bytes,
            filename=uploaded_file.name,
            uploaded_by=self.request.user,
        )

        msg_fi = (
            "IOFXML-tuonti valmis. "
            f"Kilpailuja luotu: {report.competitions_created}, "
            f"päivitetty: {report.competitions_updated}. "
            f"Ratoja luotu: {report.courses_created}. "
            f"Urheilijoita luotu: {report.athletes_created}. "
            f"Tuloksia luotu: {report.results_created}, "
            f"päivitetty: {report.results_updated}. "
            f"Väliaikoja luotu: {report.splits_created}."
        )
        msg_en = (
            "IOFXML import completed. "
            f"Competitions created: {report.competitions_created}, "
            f"updated: {report.competitions_updated}. "
            f"Courses created: {report.courses_created}. "
            f"Athletes created: {report.athletes_created}. "
            f"Results created: {report.results_created}, "
            f"updated: {report.results_updated}. "
            f"Splits created: {report.splits_created}."
        )

        messages.success(self.request, f"{msg_fi} / {msg_en}")
        return super().form_valid(form)


# ============================================================================
# Competitions list & detail views / Kilpailulista ja -detail
# ============================================================================


class CompetitionListView(ListView):
    """
    FI:
        Listaa kaikki kilpailut aikajärjestyksessä (uusin ensin) ja
        mahdollistaa haun kilpailun nimen, järjestäjän tai paikkakunnan perusteella.
    EN:
        List all competitions ordered by date (newest first) and
        allow searching by competition name, organiser or location.
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    paginate_by = 25

    def get_queryset(self):
        qs = Competition.objects.all().order_by("-date")
        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(organiser__icontains=query)
                | Q(location__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete: Athlete = self.object

        # Haetaan kaikki näkyvät tulokset
        results = (
            Result.objects.filter(
                athlete=athlete,
                is_public=True,
                deleted_at__isnull=True,
                course__competition__isnull=False,
            )
            .select_related("course", "course__competition")
            .order_by("-course__competition__date")
        )

        context["results"] = results

        # --- SUMMARY / STATS ---
        total_results = results.count()
        competitions = {r.course.competition_id for r in results}
        competitions_count = len(competitions)
        ok_results = results.filter(status="OK").count()

        # Paras sijoitus
        best_position = (
            results.filter(position__isnull=False)
            .order_by("position")
            .values_list("position", flat=True)
            .first()
        )

        # Viimeisin kilpailupäivä
        latest_date = (
            results.values_list("course__competition__date", flat=True).first()
            if total_results > 0
            else None
        )

        context["stats"] = {
            "competitions_count": competitions_count,
            "total_results": total_results,
            "ok_results": ok_results,
            "podiums": results.filter(position__in=[1, 2, 3]).count(),
            "best_position": best_position,
            "latest_date": latest_date,
        }

        return context



# =====================================================================
# Competition detail / Kilpailun sivu
# =====================================================================
class CompetitionDetailView(DetailView):
    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        competition = self.object

        # Haetaan radat varmasti tälle kilpailulle
        courses_qs = Course.objects.filter(competition=competition).order_by("name")
        context["courses"] = courses_qs
        context["course_count"] = courses_qs.count()

        # Yhteenveto tuloksista (ei pakollinen, mutta hyödyllinen)
        results_qs = Result.objects.filter(course__competition=competition)
        context["result_count"] = results_qs.count()
        context["ok_result_count"] = results_qs.filter(status="OK").count()

        return context


# =====================================================================
# Course results / Radan tulokset
# =====================================================================
class CourseResultsView(DetailView):
    """
    Näyttää yhden radan (Course) tulokset.
    URL: /kilpailut/<competition_id>/sarjat/<course_id>/
    """
    model = Course
    template_name = "oraw_app/competitions/course_results.html"
    pk_url_kwarg = "course_id"
    context_object_name = "course"

    def get_queryset(self):
        # Rajoitetaan lookup vain kyseisen kilpailun ratoihin,
        # jotta URL-parametrit varmasti sopivat yhteen.
        competition_id = self.kwargs["competition_id"]
        return Course.objects.filter(competition__pk=competition_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        results = (
            Result.objects.filter(course=course)
            .select_related("athlete")
            .order_by("position", "time")
        )
        context["results"] = results
        context["result_count"] = results.count()
        return context



# ============================================================================
# Course results / Sarjan tulokset
# ============================================================================


class CourseResultsView(ListView):
    """
    FI:
        Näyttää yksittäisen sarjan/radan tulokset valitussa kilpailussa.
    EN:
        Shows results for a single course in a given competition.
    """

    model = Result
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "results"

    @staticmethod
    def _format_diff_to_winner(seconds: int | None) -> str:
        """
        FI: Muotoilee ajan erotuksen (+mm:ss).
        EN: Format time difference as (+mm:ss).
        """
        if seconds is None:
            return ""
        sign = "+" if seconds >= 0 else "-"
        seconds = abs(seconds)
        minutes = seconds // 60
        secs = seconds % 60
        return f"{sign}{minutes:d}:{secs:02d}"

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        course_id = self.kwargs["course_id"]

        # Haetaan rata ja varmistetaan että se kuuluu tähän kilpailuun
        self.course = get_object_or_404(
            Course,
            pk=course_id,
            competition_id=competition_id,
        )

        qs = (
            Result.objects.filter(
                course=self.course,
                is_public=True,
                deleted_at__isnull=True,
                athlete__is_public=True,
                athlete__deleted_at__isnull=True,
            )
            .select_related("athlete", "course", "course__competition")
            .order_by("position", "finish_time_s")
        )

        # Voittajan aika (vain OK-tulokset, jos malli tukee tätä)
        if hasattr(Result, "STATUS_OK"):
            winner = (
                qs.filter(
                    status=Result.STATUS_OK,
                    finish_time_s__isnull=False,
                )
                .order_by("finish_time_s")
                .first()
            )
        else:
            winner = (
                qs.filter(
                    finish_time_s__isnull=False,
                )
                .order_by("finish_time_s")
                .first()
            )

        self.winner_time_s = winner.finish_time_s if winner else None

        # Ero voittajaan
        if self.winner_time_s is not None:
            for result in qs:
                if getattr(result, "finish_time_s", None) is not None and (
                    not hasattr(Result, "STATUS_OK")
                    or result.status == Result.STATUS_OK
                ):
                    diff = result.finish_time_s - self.winner_time_s
                    result.diff_to_winner_s = diff
                    result.diff_to_winner_display = self._format_diff_to_winner(diff)
                else:
                    result.diff_to_winner_s = None
                    result.diff_to_winner_display = ""
        else:
            for result in qs:
                result.diff_to_winner_s = None
                result.diff_to_winner_display = ""

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["competition"] = self.course.competition
        context["winner_time_s"] = getattr(self, "winner_time_s", None)
        return context


# ============================================================================
# Result detail / Yksittäinen tulos
# ============================================================================


class ResultDetailView(DetailView):
    """
    FI:
        Yksittäisen tuloksen tarkempi näkymä (voidaan näyttää esim. väliajat).
    EN:
        Detail view for a single result.
    """

    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result: Result = self.object
        context["competition"] = (
            result.course.competition if result.course_id else None
        )
        context["course"] = result.course
        # Jos haluat myöhemmin väliajat:
        # context["splits"] = Split.objects.filter(result=result).order_by("control_code")
        return context


# ============================================================================
# Athletes views / Urheilijalista ja -detail
# ============================================================================


class AthleteListView(ListView):
    """
    FI:
        Urheilijalista hakuominaisuuksilla (nimi, seura, sukupuoli).
    EN:
        Athlete list with simple search filters.
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

        name = (self.request.GET.get("name") or "").strip()
        club = (self.request.GET.get("club") or "").strip()
        gender = (self.request.GET.get("gender") or "").strip().upper()

        if name:
            qs = qs.filter(
                Q(first_name__icontains=name)
                | Q(last_name__icontains=name)
                | Q(full_name__icontains=name)
            )

        if club:
            qs = qs.filter(club__icontains=club)

        if gender in {"M", "F"}:
            qs = qs.filter(gender=gender)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["name"] = (self.request.GET.get("name") or "").strip()
        context["club"] = (self.request.GET.get("club") or "").strip()
        context["gender"] = (self.request.GET.get("gender") or "").strip().upper()
        return context


class AthleteDetailView(DetailView):
    """
    FI:
        Yksittäisen urheilijan perustiedot ja tuloshistoria.
    EN:
        Single athlete detail with result history.
    """

    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_object(self, queryset=None):
        athlete: Athlete = super().get_object(queryset)
        if not athlete.is_public or athlete.deleted_at is not None:
            raise Http404("Athlete not available")
        return athlete

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete: Athlete = self.object

        results = (
            Result.objects.filter(
                athlete=athlete,
                is_public=True,
                deleted_at__isnull=True,
                course__competition__isnull=False,
            )
            .select_related("course", "course__competition")
            .order_by("-course__competition__date")
        )

        context["results"] = results
        return context


# ============================================================================
# Signup view / Rekisteröityminen
# ============================================================================


class SignUpView(CreateView):
    """
    FI:
        Käyttäjän rekisteröityminen ORAOwl-palveluun.
    EN:
        User signup view for ORAOwl.
    """

    form_class = SignupForm
    template_name = "oraw_app/accounts/signup.html"
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)
        messages.success(self.request, "Tervetuloa ORAOwl-palveluun!")
        return response


# ============================================================================
# Admin dashboard / Hallintapaneeli
# ============================================================================


class AdminDashboardView(StaffRequiredMixin, TemplateView):
    """
    FI:
        Yksinkertainen hallintapaneeli kilpailun järjestäjille ja ylläpidolle.
    EN:
        Simple admin dashboard for organisers and admins.
    """

    template_name = "oraw_app/admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["competition_count"] = Competition.objects.count()
        context["athlete_count"] = Athlete.objects.filter(
            is_public=True,
            deleted_at__isnull=True,
        ).count()
        context["result_count"] = Result.objects.filter(
            is_public=True,
            deleted_at__isnull=True,
        ).count()

        context["user_count"] = User.objects.count()
        context["staff_count"] = User.objects.filter(is_staff=True).count()

        context["latest_competitions"] = Competition.objects.order_by("-date")[:5]

        return context


# ============================================================================
# Logout view / Uloskirjautuminen
# ============================================================================


class CustomLogoutView(LogoutView):
    """
    FI:
        Uloskirjautuminen, joka näyttää pienen onnistumisviestin.
    EN:
        Logout view that shows a small success message.
    """

    next_page = "oraw_app:home"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "Olet kirjautunut ulos.")
        return response
