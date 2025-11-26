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
    model = Competition
    template_name = "oraw_app/competitions/competition_detail.html"
    context_object_name = "competition"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["courses"] = (
            self.object.courses.all()          # <--- ei deleted_at-suodatusta
            .prefetch_related("results")
            .order_by("name")
        )
        return context


# ========================================================================
# Course results
# ========================================================================

class CourseResultsView(DetailView):
    model = Course
    pk_url_kwarg = "course_id"
    template_name = "oraw_app/competitions/course_results.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        results = (
            Result.objects.filter(
                course=course,
                is_public=True,
                deleted_at__isnull=True
            )
            .order_by("position")
            .select_related("athlete", "course", "course__competition")
        )

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

        context["splits"] = Split.objects.filter(result=result).order_by("leg")
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
            deleted_at__isnull=True
        ).order_by("last_name", "first_name")

        # Search filters
        name = self.request.GET.get("name")
        club = self.request.GET.get("club")
        gender = self.request.GET.get("gender")

        if name:
            qs = qs.filter(
                Q(first_name__icontains=name)
                | Q(last_name__icontains=name)
                | Q(display_name__icontains=name)
            )

        if club:
            qs = qs.filter(club__icontains=club)

        if gender and gender != "ALL":
            qs = qs.filter(gender=gender)

        return qs


# ========================================================================
# Athlete detail — TÄRKEIN KORJAUS / YHTEENVETO & KILPAILUHISTORIA
# ========================================================================

class AthleteDetailView(DetailView):
    model = Athlete
    template_name = "oraw_app/athletes/detail.html"
    context_object_name = "athlete"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        athlete = self.object

        # -------------------------------
        # Tulokset
        # -------------------------------
        results = (
            Result.objects.filter(
                athlete=athlete,
                is_public=True,
                deleted_at__isnull=True,
                course__competition__isnull=False,
            )
            .select_related("course", "course__competition")
            .order_by("-course__competition__date")
        )
        context["results"] = results

        # -------------------------------
        # YHTEENVETO / STATISTICS
        # -------------------------------
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

        # Read file content as bytes for the importer
        xml_bytes = uploaded_file.read()

        # Call importer with a single positional argument
        created, updated, errors = import_iofxml_result_list(xml_bytes)

        messages.success(
            self.request,
            f"Tuonti valmis: {created} uutta tulosta, {updated} päivitettyä."
        )
        if errors:
            messages.warning(
                self.request,
                f"{len(errors)} virhettä tiedostossa."
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
