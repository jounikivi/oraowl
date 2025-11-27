# ========================================================================
# Imports / Tuonnit
# ========================================================================

from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.http import Http404
from django.contrib.auth import get_user_model

from oraw_app.models import Competition, Athlete, Result, Course, Split
from oraw_app.forms import SignupForm, IOFXMLUploadForm
from oraw_app.utils.iofxml_importer import import_iofxml_result_list

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
    model = Competition
    template_name = "oraw_app/competitions/competition_list.html"
    context_object_name = "competitions"

    def get_queryset(self):
        queryset = Competition.objects.all().order_by("-date")

        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(location__icontains=query)
                | Q(organizer__icontains=query)
            )

        return queryset


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

        # All results in this competition
        results_qs = Result.objects.filter(course__competition=competition)

        # Summary numbers for the info cards
        context["courses"] = courses_qs
        context["course_count"] = courses_qs.count()
        context["result_count"] = results_qs.count()
        context["ok_result_count"] = results_qs.filter(status="OK").count()

        return context


# ========================================================================
# Course results
# ========================================================================

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
            .filter(status="OK", finish_time_s__isnull=False)
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
                and r.status == "OK"
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
# Athlete detail — summary & competition history
# ========================================================================

class AthleteDetailView(DetailView):
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete = self.object

        # All public results for this athlete
        results = (
            Result.objects.filter(
                athlete=athlete,
                is_public=True,
                course__competition__isnull=False,
            )
            .select_related("course", "course__competition")
            .order_by("-course__competition__date")
        )
        context["results"] = results

        # Summary statistics
        total_results = results.count()
        competitions = {r.course.competition_id for r in results}
        competitions_count = len(competitions)
        ok_results = results.filter(status="OK").count()

        best_position = (
            results.filter(position__isnull=False)
            .order_by("position")
            .values_list("position", flat=True)
            .first()
        )

        latest_date = (
            results.values_list("course__competition__date", flat=True).first()
            if total_results > 0
            else None
        )

        context["stats"] = {
            "total_results": total_results,
            "competitions_count": competitions_count,
            "ok_results": ok_results,
            "podiums": results.filter(position__in=[1, 2, 3]).count(),
            "best_position": best_position,
            "latest_date": latest_date,
        }

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
    template_name = "oraw_app/account/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("oraw_app:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("oraw_app:home")


class AdminDashboardView(PermissionRequiredMixin, TemplateView):
    permission_required = "oraw_app.can_access_admin"
    template_name = "oraw_app/admin/dashboard.html"
    
# ========================================================================
# User profile
# ========================================================================

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "oraw_app/accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["user_obj"] = user
        context["groups"] = user.groups.all().order_by("name")
        context["permissions"] = sorted(user.get_all_permissions())

        return context

