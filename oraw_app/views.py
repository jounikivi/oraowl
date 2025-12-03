# ========================================================================
# Imports / Tuonnit
# ========================================================================

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from oraw_app.models import Competition, Athlete, Result, Course, Split
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list


User = get_user_model()


# ========================================================================
# Home / Etusivu
# ========================================================================

class HomeView(TemplateView):
    """
    FI: Sovelluksen etusivu.
    EN: Application home page.
    """
    template_name = "oraw_app/home.html"


# ========================================================================
# Competition list + detail / Kilpailulista ja -detalji
# ========================================================================

class CompetitionListView(ListView):
    """
    FI: Julkinen kilpailulista, jossa on yksinkertainen haku.
    EN: Public competition list with a simple search.
    """
    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    paginate_by = 50

    def get_queryset(self):
        qs = Competition.objects.all().order_by("-date")

        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(location__icontains=query)
                | Q(organizer__icontains=query)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # FI: Välitetään hakusana takaisin templaatille.
        # EN: Pass the search query back to the template.
        context["search_query"] = self.request.GET.get("q", "")
        return context


class CompetitionDetailView(DetailView):
    """
    FI: Näyttää yksittäisen kilpailun yhteenvedon ja radat.
    EN: Shows a single competition with summary and course list.
    """
    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        competition = self.object

        # FI: Kaikki radat kilpailussa.
        # EN: All courses for this competition.
        courses_qs = (
            competition.courses
            .prefetch_related("results")
            .order_by("name")
        )

        # FI: Kaikki julkiset tulokset kilpailussa.
        # EN: All public results in this competition.
        results_qs = Result.objects.filter(
            course__competition=competition,
            is_public=True,
        )

        context["courses"] = courses_qs
        context["course_count"] = courses_qs.count()
        context["result_count"] = results_qs.count()
        context["ok_result_count"] = results_qs.filter(status=Result.STATUS_OK).count()

        return context


# ========================================================================
# Course results / Radan tuloslista
# ========================================================================

class CourseResultsView(DetailView):
    """
    FI: Näyttää yhden radan tuloslistan.
        Julkinen näkymä, ei vaadi kirjautumista.

    EN: Shows result list for a single course.
        Public view, no login required.
    """
    model = Course
    pk_url_kwarg = "course_id"
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        """
        FI: Lisää contextiin:
            - results: Result-oliot tälle radalle
            - competition: radan kilpailu
            - result.diff_to_winner_display: ero voittajaan (string)
            - laskee sijat, jos XML ei sisältänyt position-arvoja
            - järjestää DNF/DSQ/MP ym. listan loppuun

        EN: Adds to context:
            - results: Result objects for this course
            - competition: parent Competition
            - result.diff_to_winner_display: time difference to winner (string)
            - calculates positions if XML did not provide them
            - puts non-OK statuses (DNF/DSQ/MP/OTHER) to the bottom
        """
        context = super().get_context_data(**kwargs)
        course = self.object

        # FI: Hae kaikki julkiset tulokset tälle radalle (ei järjestystä vielä).
        # EN: Fetch all public results for this course (no ordering yet).
        base_qs = (
            Result.objects.filter(
                course=course,
                is_public=True,
            )
            .select_related("athlete", "course", "course__competition")
        )

        # FI: Selvitä voittaja: ensimmäinen OK-tulos, jolla on aika.
        # EN: Find winner: first OK result with a valid finish time.
        winner = (
            base_qs
            .filter(status=Result.STATUS_OK, finish_time_s__isnull=False)
            .order_by("finish_time_s")
            .first()
        )
        winner_time = winner.finish_time_s if winner else None

        # FI: Rakenna lista ja laske ero voittajaan.
        # EN: Build a list and compute difference to winner.
        results = []
        for r in base_qs:
            # FI: oletus: ei eroa näytettäväksi -> templaatissa "–"
            # EN: default: no diff to show -> "–" in template.
            r.diff_to_winner_display = None

            if (
                winner_time is not None
                and r.status == Result.STATUS_OK
                and r.finish_time_s is not None
            ):
                diff = r.finish_time_s - winner_time

                if diff <= 0:
                    # FI: voittaja itse
                    # EN: the winner herself/himself
                    r.diff_to_winner_display = "0"
                else:
                    minutes, seconds = divmod(diff, 60)
                    if minutes:
                        # esim. +1:23 / e.g. +1:23
                        r.diff_to_winner_display = f"+{minutes}:{seconds:02d}"
                    else:
                        # esim. +7 / e.g. +7
                        r.diff_to_winner_display = f"+{seconds}"

            results.append(r)

        # ------------------------------------------------------------
        # 6) Laske position, jos XML ei sisältänyt sitä ollenkaan
        #    Calculate position if XML did not provide it at all
        # ------------------------------------------------------------
        any_position = any(r.position is not None for r in results)

        if not any_position:
            # FI: Vain OK-tulokset joilla on aika voivat saada sijan.
            # EN: Only OK results with a time can get a position.
            ok_with_time = [
                r for r in results
                if r.status == Result.STATUS_OK and r.finish_time_s is not None
            ]

            # FI: Järjestetään ajan mukaan ja annetaan sijat 1, 2, 3, ...
            # EN: Sort by time and assign positions 1, 2, 3, ...
            ok_with_time.sort(key=lambda r: r.finish_time_s)

            current_pos = 1
            for r in ok_with_time:
                r.position = current_pos
                current_pos += 1
            # FI: Muut statukset (DNF/DSQ/MP/...) jäävät ilman position-arvoa
            #     -> templaatissa näytetään "–".
            # EN: Other statuses remain with position=None
            #     -> template shows "–".

        # ------------------------------------------------------------
        # 7) Laita DNF / DSQ / MP / OTHER listan loppuun
        #    Put non-OK statuses to the bottom of the list
        # ------------------------------------------------------------
        def sort_key(r: Result):
            # FI: OK-tulokset ensin (0), muut statukset sen jälkeen (1).
            # EN: OK results first (0), all other statuses after them (1).
            status_priority = 0 if r.status == Result.STATUS_OK else 1

            # FI: Pienempi position ensin; None -> iso arvo -> listan loppuun.
            # EN: Smaller position first; None -> large value -> bottom of list.
            pos = r.position if r.position is not None else 999_999

            # FI: Käytetään aikaa tasatilanteiden purkuun.
            # EN: Use time as tiebreaker when needed.
            time_key = r.finish_time_s if r.finish_time_s is not None else 999_999_999

            return (status_priority, pos, time_key)

        results.sort(key=sort_key)

        # FI: Lisätään tulokset ja kilpailu contextiin.
        # EN: Add results and competition to the context.
        context["results"] = results
        context["competition"] = course.competition
        return context


# ========================================================================
# Result detail (splits) / Yksittäinen tulos ja väliajat
# ========================================================================

class ResultDetailView(DetailView):
    """
    FI: Näyttää yhden tuloksen väliaikoineen.
    EN: Shows a single result with split times.
    """
    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.object

        # FI: Kaikki väliajat tälle tulokselle, seq-järjestyksessä.
        # EN: All splits for this result, ordered by seq.
        context["splits"] = (
            Split.objects
            .filter(result=result)
            .order_by("seq")
        )

        context["competition"] = result.course.competition
        context["course"] = result.course

        return context


# ========================================================================
# Athlete list / Suunnistajaluettelo
# ========================================================================

class AthleteListView(ListView):
    """
    FI: Suunnistajien lista, jossa yksinkertainen haku.
    EN: Athlete list with simple filters.
    """
    model = Athlete
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    paginate_by = 50  # FI: 50 urheilijaa per sivu / EN: 50 athletes per page

    def get_queryset(self):
        """
        FI:
        - Näyttää vain julkiset urheilijat.
        - Tukee hakua nimellä (etu- ja sukunimi), seuralla ja sukupuolella.
        - Trimmataan mahdolliset välilyönnit nimen alusta ja lopusta.

        EN:
        - Shows only public athletes.
        - Supports searching by name (first + last), club and gender.
        - Strips leading/trailing whitespace from name input.
        """
        qs = Athlete.objects.filter(
            is_public=True,
        ).order_by("last_name", "first_name")

        # FI: Haetaan hakuehdot GET-parametreista.
        # EN: Read filter values from GET parameters.
        name = self.request.GET.get("name", "")
        club = self.request.GET.get("club")
        gender = self.request.GET.get("gender")

        # FI: Poistetaan ylimääräiset välilyönnit alusta ja lopusta.
        # EN: Strip extra whitespace from beginning and end.
        name = name.strip()

        if name:
            # FI: Pilkotaan nimi osiin. Esim. "Emma Stenvall".
            # EN: Split name into parts. E.g. "Emma Stenvall".
            parts = name.split()

            if len(parts) >= 2:
                # FI: Oletetaan muoto "Etunimi Sukunimi" (tai toisin päin).
                # EN: Assume "First Last" (or reversed).
                first = parts[0]
                last = parts[-1]

                qs = qs.filter(
                    (
                        Q(first_name__icontains=first)
                        & Q(last_name__icontains=last)
                    )
                    | (
                        Q(first_name__icontains=last)
                        & Q(last_name__icontains=first)
                    )
                    | Q(public_alias__icontains=name)
                )
            else:
                # FI: Yksi sana -> haetaan sekä etu- että sukunimestä ja aliaksesta.
                # EN: Single word -> search in first name, last name, and alias.
                qs = qs.filter(
                    Q(first_name__icontains=name)
                    | Q(last_name__icontains=name)
                    | Q(public_alias__icontains=name)
                )

        if club:
            club = club.strip()
            if club:
                qs = qs.filter(club__icontains=club)

        if gender and gender != "ALL":
            qs = qs.filter(gender=gender)

        return qs



# ========================================================================
# Athlete detail / Suunnistajan detaljinäkymä
# ========================================================================

class AthleteDetailView(LoginRequiredMixin, DetailView):
    """
    FI: Näyttää yksittäisen suunnistajan profiilin ja tulokset.
    EN: Shows a single athlete with profile and result history.
    """
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete = self.object

        # FI: Kaikki julkiset tulokset tälle suunnistajalle.
        # EN: All public results for this athlete.
        athlete_results = (
            Result.objects
            .filter(athlete=athlete, is_public=True)
            .select_related("course__competition")
            .order_by("-course__competition__date")
        )

        # FI: Yksinkertaiset tilastot header-kortteja varten.
        # EN: Simple stats for header cards.
        total_results = athlete_results.count()
        ok_results = athlete_results.filter(status=Result.STATUS_OK).count()
        dnf_results = athlete_results.filter(status=Result.STATUS_DNF).count()
        dsq_results = athlete_results.filter(status=Result.STATUS_DSQ).count()

        best_position = (
            athlete_results
            .exclude(position=None)
            .order_by("position")
            .values_list("position", flat=True)
            .first()
        )

        context["results"] = athlete_results
        context["total_results"] = total_results
        context["ok_results"] = ok_results
        context["dnf_results"] = dnf_results
        context["dsq_results"] = dsq_results
        context["best_position"] = best_position

        return context


# ========================================================================
# IOFXML Upload / IOFXML-tuonti
# ========================================================================

class IOFXMLUploadView(LoginRequiredMixin, FormView):
    """
    FI: IOF Data Standard 3.0 ResultList -tiedoston upload-näkymä.
        Vain kirjautuneille käyttäjille.

    EN: IOF Data Standard 3.0 ResultList upload view.
        Only for logged-in users.
    """
    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]
        xml_bytes = uploaded_file.read()

        # FI: Importteri palauttaa yhden ImportReport-olion.
        # EN: Importer returns a single ImportReport object.
        report = import_iofxml_result_list(
            xml_bytes,
            filename=uploaded_file.name,
            uploaded_by=self.request.user,
        )

        created = getattr(report, "results_created", 0)
        updated = getattr(report, "results_updated", 0)
        warnings_list = report.warnings or []

        messages.success(
            self.request,
            f"Tuonti valmis: {created} uutta tulosta, {updated} päivitettyä."
        )

        if warnings_list:
            messages.warning(
                self.request,
                f"{len(warnings_list)} varoitusta IOFXML-tiedostosta."
            )

        return super().form_valid(form)


# ========================================================================
# Signup, logout, admin dashboard / Rekisteröinti, uloskirjautuminen, admin
# ========================================================================

class SignupView(FormView):
    """
    FI: Uuden käyttäjätilin luominen.
    EN: User signup view.
    """
    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    # success_url ei ole kriittinen, koska redirectataan LOGIN_URL:iin.
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        # FI: Luodaan käyttäjä mutta ei kirjauduta automaattisesti sisään.
        # EN: Create the user but do not log in automatically.
        form.save()

        messages.success(
            self.request,
            "Käyttäjätilin luominen onnistui. Voit nyt kirjautua sisään. "
            "— User account created successfully. You can now log in."
        )

        # FI: Ohjataan kirjautumissivulle (settings.LOGIN_URL).
        # EN: Redirect to login page (settings.LOGIN_URL).
        return redirect(settings.LOGIN_URL)


def logout_view(request):
    """
    FI: Kirjaa käyttäjän ulos ja ohjaa etusivulle.
    EN: Logs out the user and redirects to home page.
    """
    logout(request)
    return redirect("oraw_app:home")


class AdminDashboardView(PermissionRequiredMixin, TemplateView):
    """
    FI: Yksinkertainen admin-dashboard, joka vaatii erillisen oikeuden.
    EN: Simple admin dashboard requiring a custom permission.
    """
    permission_required = "oraw_app.can_access_admin"
    template_name = "oraw_app/admin/dashboard.html"


# ========================================================================
# User profile / Käyttäjäprofiili
# ========================================================================

class UserProfileView(LoginRequiredMixin, TemplateView):
    """
    FI: Näyttää kirjautuneen käyttäjän profiilin, ryhmät ja oikeudet.
    EN: Shows logged-in user's profile, groups and permissions.
    """
    template_name = "oraw_app/accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["user_obj"] = user
        context["groups"] = user.groups.all().order_by("name")
        # FI: Kaikki oikeudet string-listana, esim. "oraw_app.add_result".
        # EN: All permissions as a list of strings.
        context["permissions"] = sorted(user.get_all_permissions())

        return context


# ========================================================================
# Static pages / Staattiset sivut
# ========================================================================

class PrivacyPolicyView(TemplateView):
    """
    FI: Yksinkertainen tietosuojasivu demoa varten.
    EN: Simple privacy policy page for demo version.
    """
    template_name = "oraw_app/privacy.html"


class TermsOfUseView(TemplateView):
    """
    FI: Yksinkertaiset käyttöehdot demoa varten.
    EN: Simple terms of use page for demo version.
    """
    template_name = "oraw_app/terms.html"
