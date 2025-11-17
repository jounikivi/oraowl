
# oraw_app/views.py
from __future__ import annotations

# ============================================================================
# Imports / Tuonnit
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from oraw_app.models import Competition, Athlete, Result, Course
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list




# ============================================================================
# Home view / Etusivu
# ============================================================================
def home(request):
    """
    FI: Etusivu (staattinen placeholder).
    EN: Home page (static placeholder).
    """
    return render(request, "oraw_app/home.html")


# ============================================================================
# IOFXML upload view / IOFXML-latausnäkymä (staff-only)
# ============================================================================


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    FI: Mixin, joka varmistaa, että käyttäjä on kirjautunut ja kuuluu henkilöstöön.
    EN: Mixin that ensures the user is authenticated and is a staff member.
    """

    def test_func(self):
        """
        FI: Sallitaan vain staff-käyttäjät.
        EN: Allow only staff users.
        """
        user = self.request.user
        return bool(user and user.is_staff)


class IOFXMLUploadView(StaffRequiredMixin, FormView):
    """
    FI: IOFXML 3.0 ResultList -tiedoston lataus- ja tuontinäkymä (vain staff).
    EN: IOFXML 3.0 ResultList upload & import view (staff only).
    """

    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    def form_valid(self, form):
        """
        FI: Kun lomake on validi, luetaan XML-tiedosto, ajetaan importer ja
            näytetään käyttäjälle yhteenveto tuonnista.
        EN: When the form is valid, read the XML file, run the importer and
            show a summary message to the user.
        """
        uploaded_file = form.cleaned_data["file"]
        xml_bytes = uploaded_file.read()

        # FI: Kutsutaan korkeantason importer-funktiota.
        # EN: Call the high-level importer function.
        report = import_iofxml_result_list(
            xml_bytes,
            filename=uploaded_file.name,
            uploaded_by=self.request.user,
        )

        # FI: Rakennetaan kaksikielinen viesti raportin perusteella.
        # EN: Build a bilingual message based on the report.
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
# Competitions list & detail views / Kilpailunäkymät
# ============================================================================

class CompetitionListView(ListView):
    """
    FI:
        Listaa kaikki kilpailut aikajärjestyksessä (uusin ensin).
    EN:
        List all competitions ordered by date (newest first).
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    ordering = ["-date"]


class CompetitionDetailView(DetailView):
    """
    FI:
        Näyttää yhden kilpailun perustiedot ja siihen kuuluvat radat/sarjat.
    EN:
        Show basic information of a single competition and its courses.
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        """
        FI:
            Lisätään contextiin kilpailun radat, jotta ne voidaan näyttää
            listana templaatissa.
        EN:
            Add competition's courses into the template context.
        """
        context = super().get_context_data(**kwargs)
        context["courses"] = (
            Course.objects.filter(competition=self.object)
            .order_by("name")
        )
        return context

# ============================================================
# FI: Sarjan tulossivu
# EN: Course results view
# ============================================================


class CourseResultsView(ListView):
    """
    FI:
        Näyttää yhden radan (Course) kaikki tulokset taulukossa.
        Tulokset rajataan julkisiin (is_public=True) ja ei-poistettuihin
        (deleted_at is null) riveihin.
    EN:
        Show all results for a single course in a table. Only public and
        non-deleted results are listed.
    """

    model = Result
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "results"

    def get_queryset(self):
        """
        FI:
            Haetaan ensin rata (Course), johon kilpailu- ja kurssi-ID viittaavat.
            Sen jälkeen haetaan kaikki tulokset tälle radalle.
        EN:
            First fetch the Course referenced by competition_id and course_id,
            then fetch all results for that course.
        """
        competition_id = self.kwargs["competition_id"]
        course_id = self.kwargs["course_id"]

        # Haetaan rata ja samalla sen kilpailu (select_related).
        self.course = Course.objects.select_related("competition").get(
            id=course_id,
            competition__id=competition_id,
        )

        qs = (
            Result.objects.filter(
                course=self.course,
                is_public=True,
                deleted_at__isnull=True,
            )
            .select_related("athlete", "course", "course__competition", "control_card")
            .order_by("position", "finish_time_s")
        )
        return qs

    def get_context_data(self, **kwargs):
        """
        FI:
            Lisätään templaatille myös kilpailu ja rata, jotta otsikot ja
            breadcrumbit on helppo tehdä.
        EN:
            Add competition and course to the context for use in templates.
        """
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["competition"] = self.course.competition
        return context




# ============================================================================
# Athlete list & detail views / Urheilijanäkymät
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
        FI: Rakentaa hakuehdot ja palauttaa järjestetyn tuloksen.
        EN: Builds search filters and returns an ordered queryset.
        """
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        club = (self.request.GET.get("club") or "").strip()
        gender = (self.request.GET.get("gender") or "").strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) | Q(public_alias__icontains=q)
            )
        if club:
            qs = qs.filter(club__icontains=club)
        if gender:
            qs = qs.filter(gender=gender)

        return qs.order_by("full_name")


class AthleteDetailView(DetailView):
    """
    FI: Näyttää yksittäisen urheilijan ja hänen kilpailuhistoriansa.
    EN: Displays a single athlete with competition history.
    """
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää kilpailutulokset kontekstiin.
        EN: Adds competition results to the context.
        """
        ctx = super().get_context_data(**kwargs)
        athlete = self.object
        results = (
            Result.objects.filter(athlete=athlete)
            .select_related("course__competition")
            .order_by("-course__competition__date", "course__name")
        )
        ctx["results"] = results
        return ctx


# ============================================================================
# Signup view / Rekisteröintinäkymä
# ============================================================================


class SignUpView(FormView):
    """
    FI: Rekisteröinti omalla SignupForm-luokalla. Onnistumisen jälkeen
        käyttäjä kirjataan sisään.
    EN: Registration using custom SignupForm. Logs the user in on success.
    """
    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        """
        FI: Luo käyttäjän ja kirjaa sisään.
        EN: Create the user and log them in.
        """
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


# ============================================================================
# Logout view / Uloskirjautuminen
# ============================================================================


class CustomLogoutView(LogoutView):
    """
    FI: Uloskirjautuminen POST-metodilla ja lyhyt palauteviesti.
    EN: Logout via POST with a short feedback message.
    """
    next_page = "oraw_app:home"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "Olet kirjautunut ulos.")
        return response
