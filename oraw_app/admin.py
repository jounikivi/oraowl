# oraw_app/admin.py
from __future__ import annotations

from django.contrib import admin

from .models import (
    Athlete,
    Competition,
    Course,
    Result,
    UploadedFile,
    ControlCard,
)

# ---------------------------------------------------------------------
# Admin actions (GDPR)
# ---------------------------------------------------------------------


@admin.action(description="Anonymize selected athletes (GDPR)")
def anonymize_athletes(modeladmin, request, queryset):
    """
    FI: Piilota urheilijan henkilöllisyys julkisissa näkymissä.
    EN: Hide athlete identity in public views.
    """
    queryset.update(is_public=False, public_alias="Anonyymi")


@admin.action(description="Clear control cards for selected results (GDPR)")
def clear_control_cards(modeladmin, request, queryset):
    """
    FI: Poista leimauskorttitieto tuloksista (pyynnöstä).
    EN: Remove control card info from results (on request).
    """
    queryset.update(control_card=None)


# ---------------------------------------------------------------------
# Model admins
# ---------------------------------------------------------------------


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    """
    FI: Urheilijoiden hallinta. Näytä keskeiset tiedot ja salli suodatus.
    EN: Athlete admin. Show key fields and enable filtering.
    """

    list_display = (
        "id",
        "last_name",
        "first_name",
        "club",
        "gender",
        "year_of_birth",
        "public_alias",
        "is_public",
    )
    search_fields = ("first_name", "last_name", "public_alias", "club")
    list_filter = ("is_public", "gender", "club", "year_of_birth")
    ordering = ("last_name", "first_name")
    actions = [anonymize_athletes]


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    """
    FI: Kilpailujen hallinta. Lähdeviite (source_file) näkyviin jäljitettävyyttä varten.
    EN: Competition admin. Show source_file for provenance.
    """

    list_display = ("name", "date", "organizer", "location", "source_file")
    search_fields = ("name", "organizer", "location")
    list_filter = ("date",)
    ordering = ("-date", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    FI: Ratojen hallinta kilpailukohtaisesti.
    EN: Course admin per competition.
    """

    list_display = ("name", "competition")
    search_fields = ("name", "competition__name")
    list_filter = ("competition",)
    ordering = ("competition", "name")
    list_select_related = ("competition",)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """
    FI: Tulosten hallinta. Nopeutetaan listaa select_related:lla.
    EN: Result admin. Speed up list with select_related.
    """

    list_display = ("course", "athlete", "position", "status", "finish_time_s")
    search_fields = ("course__name", "athlete__first_name", "athlete__last_name")
    list_filter = ("course", "status")
    ordering = ("course", "position")
    actions = [clear_control_cards]
    list_select_related = ("course", "athlete")


@admin.register(ControlCard)
class ControlCardAdmin(admin.ModelAdmin):
    """
    FI: Leimauskorttien katselu (per vendor + uid).
    EN: Control card browse (by vendor + uid).
    """

    list_display = ("vendor", "uid", "notes")
    search_fields = ("uid", "notes")
    list_filter = ("vendor",)
    ordering = ("vendor", "uid")


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """
    FI: Alkuperäisten IOF-XML -tiedostojen hallinta (retention näkyvissä).
    EN: Original IOF-XML files (show retention).
    """

    list_display = (
        "original_name",
        "uploaded_at",
        "size_bytes",
        "sha256",
        "retention_until",
    )
    search_fields = ("original_name", "sha256")
    list_filter = ("uploaded_at", "retention_until")
    ordering = ("-uploaded_at",)
