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

from oraw_app.models import Competition, Athlete, Result
from oraw_app.forms import SignupForm



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



# ============================================================================
# Competitions list & detail views / Kilpailunäkymät
# ============================================================================
class CompetitionListView(ListView):
    """
    FI: Kilpailujen listaus sivutuksella ja pikahaulla (?q=).
    EN: Competition list with pagination and quick search (?q=).
    """
    model = Competition
    template_name = "oraw_app/competitions/index.html"
    context_object_name = "competitions"
    paginate_by = 20

    def get_queryset(self):
        """
        FI: Suodattaa kilpailut nimen ja järjestäjän perusteella.
        EN: Filters competitions by name and organizer.
        """
        qs = super().get_queryset().order_by("-date", "name")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(organizer__icontains=q))
        return qs


class CompetitionDetailView(DetailView):
    """
    FI: Näyttää kilpailun tiedot, radat ja tulokset.
    EN: Displays competition details, courses, and results.
    """
    model = Competition
    template_name = "oraw_app/competitions/detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää radat ja urheilijoiden tulokset kontekstiin.
        EN: Adds courses and athletes' results to the context.
        """
        ctx = super().get_context_data(**kwargs)
        competition = self.object

        # FI: Jos Course ForeignKey:ssä on related_name="courses", käytä sitä.
        # EN: If Course FK has related_name="courses", use it.
        courses = competition.courses.all().order_by("name")

        # FI: Tulokset kilpailun ratojen kautta, järjestä radan nimen, sijan ja ajan mukaan.
        # EN: Results via course->competition; order by course, position, and time.
        results = (
            Result.objects.filter(course__competition=competition)
            .select_related("athlete", "course")
            .order_by("course__name", "position", "time_seconds")
        )

        ctx["courses"] = courses
        ctx["results"] = results
        return ctx


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
