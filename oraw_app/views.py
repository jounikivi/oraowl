# oraw_app/views.py
from __future__ import annotations

# ============================================================================
# Imports / Tuonnit
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView

from oraw_app.models import Competition, Athlete, Result
from oraw_app.forms import SignupForm, IOFXMLForm
from oraw_app.utils.iofxml_importer import import_result_list


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
class UploadIOFXMLView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    FI: Staff-käyttäjien käyttöliittymä IOFXML (ResultList) -tiedoston lataukseen.
        Lukee tiedoston muistissa ja kutsuu importteria signatuurilla
        import_result_list(file_bytes=..., filename=...).

    EN: Staff-only UI for uploading an IOFXML (ResultList) file.
        Reads the file in-memory and calls the importer with
        import_result_list(file_bytes=..., filename=...).
    """
    template_name = "oraw_app/iofxml/upload.html"  # varmista, että tämä polku on käytössä
    form_class = IOFXMLForm
    success_url = reverse_lazy("oraw_app:upload_iofxml")

    def test_func(self) -> bool:
        # FI: Salli vain staff
        # EN: Allow staff users only
        return self.request.user.is_staff

    def form_valid(self, form):
        """
        FI: Lue tiedosto bytes-muotoon ja suorita importteri.
            Näytä viesti onnistumisesta/epäonnistumisesta.

        EN: Read the file as bytes and run the importer.
            Show a flash message on success/failure.
        """
        uploaded = form.cleaned_data["file"]  # IOFXMLForm has field "file"
        file_bytes = uploaded.read()
        try:
            report = import_result_list(file_bytes=file_bytes, filename=uploaded.name)
        except Exception as exc:
            messages.error(self.request, f"Tuonti epäonnistui: {exc}")
            return self.form_invalid(form)

        messages.success(
            self.request,
            "IOFXML-tuonti suoritettu onnistuneesti. Uudet kilpailut ja tulokset ovat nyt saatavilla.",
        )
        return super().form_valid(form)


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

        # FI: Käytä related_name="courses" (jos malli määritelty niin)
        # EN: Use related_name="courses" (if defined in model)
        courses = competition.courses.all().order_by("name")

        # FI: Tulokset kilpailun ratojen kautta, lajittelu radan nimen ja sijoituksen sekä ajan mukaan
        # EN: Results via course -> competition relation, ordered by course name, position and time
        results = (
            Result.objects
            .filter(course__competition=competition)
            .select_related("athlete", "course")
            .order_by("course__name", "position", "time_seconds")  # 'time_seconds' matches your model
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
            # FI: Teidän mallissa käytetään yleensä 'full_name' + 'public_alias'
            # EN: In your model you typically have 'full_name' + 'public_alias'
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(public_alias__icontains=q)
            )
        if club:
            qs = qs.filter(club__icontains=club)
        if gender:
            qs = qs.filter(gender=gender)

        return qs.order_by("full_name")


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
            Result.objects
            .filter(athlete=athlete)
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


# ============================================================================
# Logout view / Uloskirjautuminen
# ============================================================================
class CustomLogoutView(LogoutView):
    """
    FI: Uloskirjautuminen POST-metodilla. Lisää myös onnistumisviestin.
    EN: Logout via POST method. Adds a success message.
    """
    next_page = "oraw_app:home"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "Olet kirjautunut ulos onnistuneesti.")
        return response
