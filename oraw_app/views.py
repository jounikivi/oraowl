from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from oraw_app.models import Competition


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
