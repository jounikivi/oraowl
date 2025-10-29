from __future__ import annotations

from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from oraw_app.models import Competition, Athlete, Result


def home(request):
    """
    FI: Etusivu (staattinen placeholder).
    EN: Home page (static placeholder).
    """
    return render(request, "oraw_app/home.html")


class UploadIOFXMLView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    FI: Staff-käyttäjien UI IOFXML-tuonnille. Kutsuu olemassa olevaa
        'import_iofxml' -management-komentoa, jotta UI ja CLI toimivat identtisesti.

    EN: Staff-only UI for IOFXML import. Calls the existing 'import_iofxml'
        management command to keep behavior identical with CLI imports.
    """
    template_name = "oraw_app/upload_iofxml.html"

    def test_func(self) -> bool:
        """
        FI: Vain staff-käyttäjät saavat käyttää tätä näkymää.
        EN: Only staff users are allowed to access this view.
        """
        return self.request.user.is_staff

    def get(self, request):
        """
        FI: Palauta lomakenäkymä.
        EN: Render the form view.
        """
        return render(request, self.template_name)

    def post(self, request):
        """
        FI: Käsittele IOFXML-lähetys: talleta väliaikaisesti ja aja import-komento.
        EN: Handle IOFXML upload: save temporarily and run the import command.
        """
        f = request.FILES.get("iofxml_file")
        if not f:
            messages.error(request, "Upload failed: missing file.")
            return render(request, self.template_name)

        # FI: Tallenna väliaikaiseen polkuun, jotta management-komento voi lukea tiedoston.
        # EN: Save to a temporary path so the management command can read the file.
        tmp_path = default_storage.save(f"tmp/iofxml/{f.name}", f)

        try:
            # FI: Kutsu samaa komentoa kuin CLI:ssä (yhden totuuden lähde).
            # EN: Call the same command as in CLI (single source of truth).
            call_command("import_iofxml", file=default_storage.path(tmp_path))
            messages.success(
                request,
                "IOFXML import finished successfully. " 
                "New competitions and results are now available.",
            )
            return redirect(reverse("oraw_app:upload_iofxml"))
        except Exception as exc:
            # FI: Näytä käyttäjäystävällinen virheviesti.
            # EN: Show a user-friendly error message.
            messages.error(request, f"Import failed: {exc}")
            return render(request, self.template_name)

class CompetitionListView(ListView):
    """
    FI: Kilpailujen listaus sivutuksella ja pikahaulla (?q=).
    EN: Competitions list with pagination and quick search (?q=).
    """
    model = Competition
    template_name = "oraw_app/competitions/index.html"
    context_object_name = "competitions"
    paginate_by = 20

    def get_queryset(self):
        """
        FI: Suodata nimen ja järjestäjän perusteella.
        EN: Filter by name and organizer.
        """
        qs = super().get_queryset().order_by("-date", "name")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(organizer__icontains=q)
        return qs


class CompetitionDetailView(DetailView):
    """
    FI: Kilpailun sivu: radat ja kevyt tulostaulukko.
    EN: Competition page: courses and a lightweight results table.
    """
    model = Competition
    template_name = "oraw_app/competitions/detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        """
        FI: Lataa radat ja esilataa tulosten urheilijat (GDPR-näyttö).
        EN: Load courses and prefetch results with athletes (GDPR display).
        """
        ctx = super().get_context_data(**kwargs)
        competition = self.object
        courses = competition.course_set.all().order_by("name")
        ctx["courses"] = courses.prefetch_related("result_set__athlete")
        return ctx


class AthleteListView(ListView):
    """
    FI: Näyttää kaikki urheilijat taulukkona ja tukee hakuparametreja (?q, ?club, ?gender).
    EN: Displays all athletes in a table, supports query parameters (?q, ?club, ?gender).
    """
    model = Athlete  # malli, jota tämä näkymä käyttää
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    paginate_by = 25  # näyttää 25 urheilijaa per sivu

    def get_queryset(self):
        """
        FI: Rakentaa tietokantakyselyn hakuehtojen perusteella.
        EN: Builds a database query based on search parameters.
        """
        qs = super().get_queryset()  # perusjoukko = kaikki urheilijat

        # Haetaan GET-parametrit (jos niitä ei ole, palautetaan tyhjä merkkijono)
        q = (self.request.GET.get("q") or "").strip()
        club = (self.request.GET.get("club") or "").strip()
        gender = (self.request.GET.get("gender") or "").strip()

        # Jos käyttäjä kirjoittaa nimen, suodata nimen ja aliaksen perusteella
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(public_alias__icontains=q)
            )

        # Jos käyttäjä valitsee seuran
        if club:
            qs = qs.filter(club__icontains=club)

        # Jos käyttäjä valitsee sukupuolen
        if gender:
            qs = qs.filter(gender=gender)

        # Järjestetään tulokset
        return qs.order_by("last_name", "first_name")

class AthleteDetailView(DetailView):
    """
    FI: Näyttää yksittäisen urheilijan perustiedot ja kilpailuhistorian.
    EN: Displays a single athlete with basic info and competition history.
    """
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää urheilijan kilpailutulokset kontekstiin (HTML:lle).
        EN: Adds athlete's competition results to the template context.
        """
        ctx = super().get_context_data(**kwargs)
        athlete = self.object  # haettu Athlete-olio
        results = (
            Result.objects.filter(athlete=athlete)
            .select_related("course__competition")
            .order_by("-course__competition__date", "course__name")
        )
        ctx["results"] = results
        return ctx
