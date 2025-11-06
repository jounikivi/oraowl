# oraw_app/views.py
from __future__ import annotations

# ============================================================================
# Imports / Tuonnit
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth import login

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
# IOFXML upload view / IOFXML-latausnäkymä
# ============================================================================
class UploadIOFXMLView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    FI: Staff-käyttäjien käyttöliittymä IOFXML-tiedoston tuontiin.
        Kutsuu olemassa olevaa 'import_iofxml'-komentoa, jotta UI ja CLI toimivat
        identtisesti (yksi totuuden lähde).

    EN: Staff-only UI for IOFXML import.
        Calls the 'import_iofxml' management command to ensure identical behavior
        with the CLI importer.
    """
    template_name = "oraw_app/upload_iofxml.html"

    def test_func(self) -> bool:
        """
        FI: Sallitaan käyttö vain staff-käyttäjille.
        EN: Allow access only for staff users.
        """
        return self.request.user.is_staff

    def get(self, request):
        """
        FI: Palauttaa tyhjän lomakenäkymän.
        EN: Render the empty upload form.
        """
        return render(request, self.template_name)

    def post(self, request):
        """
        FI: Käsittelee tiedoston latauksen ja suorittaa tuonnin komentona.
        EN: Handles file upload and executes the import as a management command.
        """
        f = request.FILES.get("iofxml_file")
        if not f:
            messages.error(request, "Lataus epäonnistui: tiedosto puuttuu.")
            return render(request, self.template_name)

        # Save file temporarily for import
        tmp_path = default_storage.save(f"tmp/iofxml/{f.name}", f)

        try:
            call_command("import_iofxml", file=default_storage.path(tmp_path))
            messages.success(
                request,
                "IOFXML-tuonti suoritettu onnistuneesti. "
                "Uudet kilpailut ja tulokset ovat nyt saatavilla.",
            )
            return redirect(reverse("oraw_app:upload_iofxml"))
        except Exception as exc:
            messages.error(request, f"Tuonti epäonnistui: {exc}")
            return render(request, self.template_name)


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
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(organizer__icontains=q))
        return qs


class CompetitionDetailView(DetailView):
    """
    FI: Näyttää kilpailun tiedot, radat ja tulokset.
    EN: Displays competition details, courses and results.
    """
    model = Competition
    template_name = "oraw_app/competitions/detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää radat ja urheilijoiden tulokset kontekstiin.
        EN: Adds courses and athletes’ results to the context.
        """
        ctx = super().get_context_data(**kwargs)
        competition = self.object
        courses = competition.course_set.all().order_by("name")
        ctx["courses"] = courses.prefetch_related("result_set__athlete")
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
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(public_alias__icontains=q)
            )
        if club:
            qs = qs.filter(club__icontains=club)
        if gender:
            qs = qs.filter(gender=gender)

        return qs.order_by("last_name", "first_name")


class AthleteDetailView(DetailView):
    """
    FI: Näyttää yksittäisen urheilijan ja hänen kilpailuhistoriansa.
    EN: Displays an athlete with competition history.
    """
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää kilpailutulokset kontekstiin, jotta ne voidaan näyttää HTML-sivulla.
        EN: Adds competition results to context for template rendering.
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
    FI: Käyttäjän rekisteröinti. Käyttää omaa SignupForm-luokkaa (forms.py),
        joka sisältää suomenkieliset kenttien nimet ja yhtenäisen ulkoasun.
        Onnistuneen rekisteröinnin jälkeen käyttäjä kirjataan sisään.

    EN: User registration using the custom SignupForm (forms.py)
        with localized Finnish labels and consistent layout.
        Logs the user in automatically after successful registration.
    """
    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        """
        FI: Luo käyttäjän ja kirjaa hänet sisään automaattisesti.
        EN: Creates the user and logs them in automatically.
        """
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)
