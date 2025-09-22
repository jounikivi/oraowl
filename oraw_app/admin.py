# oraw_app/admin.py
from __future__ import annotations

from django.contrib import admin
from .models import Athlete, Competition, Course, Result, UploadedFile


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("id", "last_name", "first_name", "public_alias", "is_public")
    search_fields = ("first_name", "last_name", "public_alias")
    list_filter = ("is_public",)
    ordering = ("last_name", "first_name")


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "organizer", "location", "source_file")
    search_fields = ("name", "organizer", "location")
    list_filter = ("date",)
    ordering = ("-date", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "competition")
    search_fields = ("name", "competition__name")
    list_filter = ("competition",)
    ordering = ("competition", "name")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("course", "athlete", "position", "status", "finish_time_s")
    search_fields = ("course__name", "athlete__first_name", "athlete__last_name")
    list_filter = ("course", "status")
    ordering = ("course", "position")


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "uploaded_at", "size_bytes", "sha256")
    search_fields = ("original_name", "sha256")
    list_filter = ("uploaded_at",)
    ordering = ("-uploaded_at",)
