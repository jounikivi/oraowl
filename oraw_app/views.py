# ========================================================================
# Imports / Tuonnit
# ========================================================================

from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
#from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.contrib.auth import login, logout
from django.shortcuts import redirect
#from django.contrib.auth.views import LogoutView
#from django.http import Http404
from django.contrib.auth import get_user_model

from oraw_app.models import Competition, Athlete, Result, Course, Split
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list
from django.conf import settings

User = get_user_model()


# ========================================================================
# Home
# ========================================================================

class HomeView(TemplateView):
    template_name = "oraw_app/home.html"


# ========================================================================
# Competition list + detail
# ========================================================================

class CompetitionListView(ListView):
    """
    Public competition list with simple search and pagination.
    """
    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"
    paginate_by = 20  # show 20 competitions per page

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
        # so template can easily re-fill the search box
        context["search_query"] = self.request.GET.get("q", "")
        return context


class CompetitionDetailView(DetailView):
    """
    Shows single competition with summary cards and list of courses.
    """
    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        competition = self.object

        # All courses for this competition
        courses_qs = (
            competition.courses
            .prefetch_related("results")
            .order_by("name")
        )

        # All public results in this competition
        results_qs = Result.objects.filter(
            course__competition=competition,
            is_public=True,
        )

        # Summary numbers for the info cards
        context["courses"] = courses_qs
        context["course_count"] = courses_qs.count()
        context["result_count"] = results_qs.count()
        context["ok_result_count"] = results_qs.filter(status="OK").count()

        return context


# ========================================================================
# Course results view
# ========================================================================

class CourseResultsView(DetailView):
    """
    Shows result list for a single course.
    Public view: no login required.
    """
    model = Course
    pk_url_kwarg = "course_id"
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        """
        Adds:
        - results: list of Result objects for this course
        - competition: parent Competition
        - result.diff_to_winner_display: time difference to course winner
        - laskee tarvittaessa sijan (position), jos sitä ei ole XML:ssä
        """
        context = super().get_context_data(**kwargs)
        course = self.object

        # Hae kaikki julkiset tulokset tälle radalle
        results_qs = (
            Result.objects.filter(
                course=course,
                is_public=True,
            )
            .order_by("position")
            .select_related("athlete", "course", "course__competition")
        )

        # Selvitä voittaja: ensimmäinen OK-tulos, jolla on aika
        winner = (
            results_qs
            .filter(status=Result.STATUS_OK, finish_time_s__isnull=False)
            .order_by("finish_time_s")
            .first()
        )
        winner_time = winner.finish_time_s if winner else None

        # Laske ero voittajaan jokaiselle tulokselle
        results = []
        for r in results_qs:
            r.diff_to_winner_display = None  # oletus, templaten "–"

            if (
                winner_time is not None
                and r.status == Result.STATUS_OK
                and r.finish_time_s is not None
            ):
                diff = r.finish_time_s - winner_time

                if diff <= 0:
                    # voittaja itse
                    r.diff_to_winner_display = "0"
                else:
                    minutes, seconds = divmod(diff, 60)
                    if minutes:
                        # esim. +1:23
                        r.diff_to_winner_display = f"+{minutes}:{seconds:02d}"
                    else:
                        # esim. +7
                        r.diff_to_winner_display = f"+{seconds}"

            results.append(r)

        # ------------------------------------------------------------
        # KOHTA 6: Laske position, jos XML ei sisältänyt sitä ollenkaan
        # ------------------------------------------------------------
        any_position = any(r.position is not None for r in results)

        if not any_position:
            # Otetaan vain OK-tulokset, joilla on aika
            ok_with_time = [
                r for r in results
                if r.status == Result.STATUS_OK and r.finish_time_s is not None
            ]

            # Järjestetään ne ajan mukaan
            ok_with_time.sort(key=lambda r: r.finish_time_s)

            # Annetaan sijat 1, 2, 3, ...
            current_pos = 1
            for r in ok_with_time:
                r.position = current_pos
                current_pos += 1
            # DNF/DSQ/MP ym. jäävät ilman position-arvoa -> templaatissa näkyy "–"

        context["results"] = results
        context["competition"] = course.competition
        return context

# ========================================================================
# Result detail (Splits)
# ========================================================================

class ResultDetailView(DetailView):
    model = Result
    template_name = "oraw_app/competitions/result_detail.html"
    context_object_name = "result"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.object

        # Hae kaikki väliajat tälle tulokselle, järjestys numeron (seq) mukaan
        context["splits"] = (
            Split.objects
            .filter(result=result)
            .order_by("seq")
        )

        context["competition"] = result.course.competition
        context["course"] = result.course

        return context


# ========================================================================
# Athlete list
# ========================================================================

class AthleteListView(ListView):
    model = Athlete
    template_name = "oraw_app/athletes/index.html"
    context_object_name = "athletes"
    
    paginate_by = 50

    def get_queryset(self):
        qs = Athlete.objects.filter(
            is_public=True,
        ).order_by("last_name", "first_name")

        # Search filters
        name = self.request.GET.get("name")
        club = self.request.GET.get("club")
        gender = self.request.GET.get("gender")
        
        if name:
            qs = qs.filter(
                Q(first_name__icontains=name)
                | Q(last_name__icontains=name)
                | Q(public_alias__icontains=name)
            )


        if club:
            qs = qs.filter(club__icontains=club)

        if gender and gender != "ALL":
            qs = qs.filter(gender=gender)

        return qs


# ========================================================================
# Athlete detail
# ========================================================================

class AthleteDetailView(LoginRequiredMixin, DetailView):
    """
    Shows a single athlete with basic profile information and
    a list of their results.
    """
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete = self.object

        # All public results for this athlete
        athlete_results = (
            Result.objects
            .filter(athlete=athlete, is_public=True)
            .select_related("course__competition")
            .order_by("-course__competition__date")
        )

        # Simple stats for header cards
        total_results = athlete_results.count()
        ok_results = athlete_results.filter(status="OK").count()
        dnf_results = athlete_results.filter(status="DNF").count()
        dsq_results = athlete_results.filter(status="DSQ").count()

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
# IOF XML Upload
# ========================================================================

class IOFXMLUploadView(LoginRequiredMixin, FormView):
    template_name = "oraw_app/iofxml/upload.html"
    form_class = IOFXMLUploadForm
    success_url = reverse_lazy("oraw_app:iofxml_upload")

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]
        xml_bytes = uploaded_file.read()

        # Import returns a single ImportReport object
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
# Signup, Logout, Admin dashboard
# ========================================================================

class SignupView(FormView):
    template_name = "oraw_app/accounts/signup.html"
    form_class = SignupForm
    # success_url ei ole nyt niin tärkeä, mutta voi jäädä varalle
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        # 1) Luodaan käyttäjätili
        form.save()

        # 2) Lisätään onnistumisviesti
        messages.success(
            self.request,
            "Käyttäjätilin luominen onnistui. Voit nyt kirjautua sisään. "
            "— User account created successfully. You can now log in."
)


        # 3) Ohjataan login-sivulle käyttäen settings.LOGIN_URL
        #    -> ei rikota mitään, vaikka URL-nimi olisi jotain muuta
        return redirect(settings.LOGIN_URL)


def logout_view(request):
    """
    Kirjaa käyttäjän ulos ja ohjaa etusivulle.
    Sallii tavallisen GET-pyynnön (napin klikkaus).
    """
    logout(request)
    return redirect("oraw_app:home")


class AdminDashboardView(PermissionRequiredMixin, TemplateView):
    permission_required = "oraw_app.can_access_admin"
    template_name = "oraw_app/admin/dashboard.html"
    
# ========================================================================
# User profile
# ========================================================================

class UserProfileView(LoginRequiredMixin, TemplateView):
    """
    Shows the logged-in user's profile information, groups and permissions.
    """
    template_name = "oraw_app/accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["user_obj"] = user
        context["groups"] = user.groups.all().order_by("name")
        # permissions as a sorted list of strings, e.g. "oraw_app.add_result"
        context["permissions"] = sorted(user.get_all_permissions())

        return context

    
    
# ========================================================================

class PrivacyPolicyView(TemplateView):
    """Static privacy policy page for demo version."""
    template_name = "oraw_app/privacy.html"


class TermsOfUseView(TemplateView):
    """Static terms of use page for demo version."""
    template_name = "oraw_app/terms.html"

