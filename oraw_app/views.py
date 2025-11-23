# oraw_app/views.py
from __future__ import annotations

# ============================================================================
# Imports / Tuonnit
# ============================================================================
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.http import Http404
from oraw_app.models import Competition, Athlete, Result, Course, Split
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


class IOFXMLUploadView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    FI: IOFXML 3.0 ResultList -tiedoston lataus- ja tuontinäkymä.
    EN: IOFXML 3.0 ResultList upload & import view.
    """

    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    # FI: Vain käyttäjät, joilla on tämä oikeus, saavat käyttää näkymää.
    # EN: Only users with this permission may access the view.
    permission_required = "oraw_app.can_import_iofxml"
    raise_exception = True  # -> 403 jos kirjautunut mutta ei lupaa

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

# ============================================================================
# Competitions list & detail views / Kilpailunäkymät
# ============================================================================

class CompetitionDetailView(DetailView):
    """
    FI:
        Näyttää yhden kilpailun perustiedot ja siihen kuuluvat radat/sarjat.
        Lisäksi lasketaan pieni yhteenveto:
        - sarjojen määrä
        - tulosten määrä
        - OK-tulosten määrä
    EN:
        Show basic information of a single competition and its courses.
        Also provides a small summary:
        - number of courses
        - number of results
        - number of OK results
    """

    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        """
        FI:
            Lisätään contextiin:
              - courses: kilpailun radat
              - summary: pieni tilastoyhteenveto kilpailusta
            Käytetään vain julkisia (GDPR) tuloksia yhteenvetoon.
        EN:
            Add to context:
              - courses: competition courses
              - summary: small statistics summary for the competition
            Uses only public (GDPR-safe) results for the summary.
        """
        context = super().get_context_data(**kwargs)
        competition: Competition = self.object

        # Kilpailun radat / Courses for this competition
        courses_qs = Course.objects.filter(competition=competition).order_by("name")
        context["courses"] = courses_qs

        # Julkiset tulokset tältä kilpailulta (GDPR-suodatus)
        results_qs = Result.objects.filter(
            course__competition=competition,
            is_public=True,
            deleted_at__isnull=True,
            athlete__is_public=True,
            athlete__deleted_at__isnull=True,
        )

        context["summary"] = {
            "courses_count": courses_qs.count(),
            "results_count": results_qs.count(),
            "ok_results_count": results_qs.filter(status="OK").count(),
        }

        return context



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
    paginate_by = 25  # tarvittaessa voit säätää tai poistaa tämän

    def get_queryset(self):
        """
        FI:
            Palauttaa kilpailut uusimmasta vanhimpaan. Jos 'q'-parametri on mukana
            GET-kyselyssä, suodatetaan kilpailuja nimen, järjestäjän tai paikkakunnan
            perusteella (osittainen haku, ei kirjainkoolla väliä).
        EN:
            Returns competitions ordered from newest to oldest. If 'q' parameter
            is present in the GET request, filter competitions by name, organiser
            or location (partial, case-insensitive match).
        """
        qs = Competition.objects.all().order_by("-date")

        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(organizer__icontains=query)
                | Q(location__icontains=query)
            )

        return qs

    def get_context_data(self, **kwargs):
        """
        FI:
            Lisätään hakusana contextiin, jotta se voidaan näyttää hakukentässä
            competition_list-templaatissa.
        EN:
            Add the current search query into the context so it can be shown
            in the search field in the competition_list template.
        """
        context = super().get_context_data(**kwargs)
        context["q"] = (self.request.GET.get("q") or "").strip()
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
        (deleted_at is null) riveihin. Lisäksi piilotetaan ei-julkisten
        urheilijoiden tulokset (GDPR).

        Tässä versiossa lasketaan myös voittajan aika ja
        "ero voittajaan" jokaiselle OK-tulokselle.
    EN:
        Show all results for a single course in a table. Only public and
        non-deleted results are listed and results for non-public athletes
        are hidden (GDPR).

        This version also computes the winner time and the time difference
        to the winner for each OK result.
    """

    model = Result
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "results"

    @staticmethod
    def _format_diff_to_winner(seconds: int) -> str:
        """
        FI: Muuntaa sekunnit muotoon +M:SS tai +H:MM:SS.
        EN: Convert seconds to +M:SS or +H:MM:SS format.
        """
        if seconds is None:
            return ""
        # varmuuden vuoksi int ja positiivinen arvo
        total = int(seconds)
        sign = "+" if total >= 0 else "-"
        total = abs(total)
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            base = f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            base = f"{minutes}:{secs:02d}"
        return f"{sign}{base}"

    def get_queryset(self):
        """
        FI:
            Haetaan rata (Course) URL-parametrien perusteella ja sen julkiset
            tulokset. Samalla alustetaan self.course ja self.winner_time_s
            sekä lisätään jokaiselle Result-instanssille attribuutit
            diff_to_winner_s ja diff_to_winner_display.

        EN:
            Fetch the Course based on URL kwargs and then all public results
            for that course. Also sets self.course and self.winner_time_s
            and attaches diff_to_winner_s and diff_to_winner_display
            attributes to each Result instance.
        """
        competition_id = self.kwargs["competition_id"]
        course_id = self.kwargs["pk"]  # <uuid:pk> from URL

        # Haetaan rata ja varmistetaan, että se kuuluu tälle kilpailulle.
        self.course = Course.objects.select_related("competition").get(
            id=course_id,
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
            .select_related(
                "athlete",
                "course",
                "course__competition",
                "control_card",
            )
            .order_by("position", "finish_time_s")
        )

        # Selvitetään voittajan aika (nopein OK-tulos, jolla on aika).
        winner = (
            qs.filter(
                status=Result.STATUS_OK,
                finish_time_s__isnull=False,
            )
            .order_by("finish_time_s")
            .first()
        )
        self.winner_time_s = winner.finish_time_s if winner else None

        # Lisätään jokaiselle Result-oliolle diff-attribuutit.
        if self.winner_time_s is not None:
            for result in qs:
                if (
                    result.finish_time_s is not None
                    and result.status == Result.STATUS_OK
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
        """
        FI:
            Lisätään templaatille myös kilpailu, rata ja voittajan aika,
            jotta otsikot ja breadcrumbit on helppo tehdä ja voittajan
            aika voidaan haluttaessa näyttää.

        EN:
            Add competition, course and winner time into template context.
        """
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["competition"] = self.course.competition
        context["winner_time_s"] = getattr(self, "winner_time_s", None)
        return context



# ============================================================
# FI: Yksittäisen tuloksen väliaikasivu
# EN: Single result split times view
# ============================================================


class ResultDetailView(DetailView):
    """
    FI:
        Näyttää yhden tuloksen perustiedot sekä kaikki väliajat taulukossa.
        Käyttää Result-olion lisäksi Split-mallia väliaikojen hakuun.
        Jos tulos tai urheilija ei ole julkinen, palautetaan 404 (GDPR).
    EN:
        Show a single result with its basic information and all split times
        in a table. Uses the Split model to fetch split data.
        If the result or athlete is not public, return 404 (GDPR).
    """

    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_context_data(self, **kwargs):
        """
        FI:
            Lisätään templaatille:
              - competition: kilpailu
              - course: rata / sarja
              - athlete: urheilija
              - splits: väliajat järjestettynä järjestysnumeron mukaan
            Sekä tarkistetaan tietosuoja: jos tulos tai urheilija on piilotettu,
            heitetään 404.
        EN:
            Add to the template context:
              - competition
              - course
              - athlete
              - splits ordered by sequence
            Also enforce privacy: if the result or athlete is hidden,
            raise 404.
        """
        context = super().get_context_data(**kwargs)

        result: Result = self.object
        athlete = result.athlete

        # Tietosuoja / Privacy check
        if (
            not result.is_public
            or result.deleted_at is not None
            or not athlete.is_public
            or athlete.deleted_at is not None
        ):
            raise Http404("Result is not public")

        competition = result.course.competition
        course = result.course

        # Haetaan kaikki väliajat (Split) tälle tulokselle.
        splits = Split.objects.filter(result=result).order_by("seq")

        context["competition"] = competition
        context["course"] = course
        context["athlete"] = athlete
        context["splits"] = splits
        return context


# ============================================================================
# Athlete list & detail views / Urheilijanäkymät
# ============================================================================


class AthleteListView(ListView):
    """
    FI:
        Urheilijalista taulukkona, tukee hakua ja suodatuksia
        (?q, ?club, ?gender). Näyttää vain julkiset (is_public=True) ja
        ei-poistetut (deleted_at is null) urheilijat.
    EN:
        Athlete list with filters (?q, ?club, ?gender). Shows only public
        and non-deleted athletes.
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

        Jos urheilija ei ole julkinen tai hänet on merkitty poistetuksi,
        ei näytetä kilpailuhistoriaa (GDPR).

    EN:
        Displays the athlete profile and competition history.
        Also provides a small stats summary:
        - number of competitions
        - number of results
        - number of OK results
        - podium finishes (1–3)
        - best position
        - date of latest competition

        If the athlete is not public or soft-deleted, competition
        history is hidden (GDPR).
    """

    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        athlete = self.object

        # ------------------------------------------------------------
        # FI: Jos urheilija ei ole julkinen tai merkitty poistetuksi,
        #     ei näytetä kilpailuhistoriaa.
        # EN: If athlete is not public or soft-deleted, do not show
        #     competition history.
        # ------------------------------------------------------------
        if not athlete.is_public or athlete.deleted_at is not None:
            ctx["is_hidden"] = True
            ctx["results"] = Result.objects.none()
            ctx["stats"] = {
                "total_results": 0,
                "competitions_count": 0,
                "ok_results": 0,
                "podiums": 0,
                "best_position": None,
                "latest_date": None,
            }
            return ctx

        ctx["is_hidden"] = False

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
