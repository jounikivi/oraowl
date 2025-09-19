# oraw_app/admin.py
from django.contrib import admin
from .models import (
    Athlete,
    AthleteIdentifier,
    Competition,
    Course,
    Result,
    PrivacyPreference,
    AuditLog,
    UploadedFile,
    Split,
)

# ---------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------


class AthleteIdentifierInline(admin.TabularInline):
    model = AthleteIdentifier
    extra = 0
    fields = ("id_type", "value")
    readonly_fields = ()
    can_delete = True


class SplitInline(admin.TabularInline):
    model = Split
    extra = 0
    fields = ("seq", "control_code", "time_s", "leg_time_s", "note")
    readonly_fields = ()
    can_delete = True


# ---------------------------------------------------------------------
# Admin actions (FI/EN)
# ---------------------------------------------------------------------


# FI: Piilota valittujen urheilijoiden nimi julkisesta näkymästä.
# EN: Hide selected athletes' real names from public views.
def action_hide_athlete_names(modeladmin, request, queryset):
    queryset.update(is_public=False)
    for ath in queryset:
        AuditLog.objects.create(
            athlete=ath,
            event="hide_name",
            reason="Admin action",
            by=str(request.user),
            data_category="identity",
            processing_basis="legitimate_interest",
        )


action_hide_athlete_names.short_description = "Hide real name (selected athletes)"


# FI: Näytä nimi taas julkisesti.
# EN: Show real name publicly again.
def action_show_athlete_names(modeladmin, request, queryset):
    queryset.update(is_public=True)
    for ath in queryset:
        AuditLog.objects.create(
            athlete=ath,
            event="show_name",
            reason="Admin action",
            by=str(request.user),
            data_category="identity",
            processing_basis="legitimate_interest",
        )


action_show_athlete_names.short_description = "Show real name (selected athletes)"


# FI: Anonymisoi valitut urheilijat kevyesti (alias + tyhjennä tunnisteet).
# EN: Light anonymization: set alias, clear identifiers.
def action_anonymize_athletes(modeladmin, request, queryset):
    for ath in queryset:
        # Set a simple alias if missing
        if not ath.public_alias:
            ath.public_alias = f"Athlete-{str(ath.id)[:8]}"
        ath.is_public = False
        ath.save(update_fields=["public_alias", "is_public"])
        # Remove identifiers
        AthleteIdentifier.objects.filter(athlete=ath).delete()
        AuditLog.objects.create(
            athlete=ath,
            event="anonymize",
            reason="Admin action",
            by=str(request.user),
            data_category="identity",
            processing_basis="legitimate_interest",
        )


action_anonymize_athletes.short_description = "Anonymize (selected athletes)"


# FI: Piilota valitut tulokset (GDPR, virhe, pyyntö).
# EN: Hide selected results from public views.
def action_hide_results(modeladmin, request, queryset):
    queryset.update(is_visible=False)
    for res in queryset:
        AuditLog.objects.create(
            athlete=res.athlete,
            event="hide_result",
            reason="Admin action",
            by=str(request.user),
            data_category="performance",
            processing_basis="legitimate_interest",
        )


action_hide_results.short_description = "Hide (selected results)"


# ---------------------------------------------------------------------
# ModelAdmins
# ---------------------------------------------------------------------


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    """
    FI: Urheilijan hallinta. Pikatoiminnot: hide/show/anonymize.
    EN: Athlete management with quick actions: hide/show/anonymize.
    """

    list_display = (
        "last_name",
        "first_name",
        "club",
        "gender",
        "birth_year",
        "is_public",
        "deleted_at",
    )
    search_fields = (
        "last_name",
        "first_name",
        "club",
        "public_alias",
        "identifiers__value",
    )
    list_filter = ("is_public", "gender", "deleted_at")
    inlines = (AthleteIdentifierInline,)
    actions = (
        action_hide_athlete_names,
        action_show_athlete_names,
        action_anonymize_athletes,
    )


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    """FI/EN: Competition management."""

    list_display = ("name", "date", "organizer", "location", "source_name")
    search_fields = ("name", "organizer", "location", "source_name")
    list_filter = ("date",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """FI/EN: Course management."""

    list_display = ("name", "competition", "length_km", "clazz")
    search_fields = ("name", "competition__name", "clazz")
    list_filter = ("competition",)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """
    FI: Tulosten hallinta. Inline-splitit ja pikatoiminto piilottamiseen.
    EN: Result management. Inline splits and hide action.
    """

    list_display = (
        "athlete",
        "course",
        "status",
        "finish_time_s",
        "pace_s_per_km",
        "position",
        "is_visible",
    )
    search_fields = (
        "athlete__last_name",
        "athlete__first_name",
        "course__name",
        "course__competition__name",
    )
    list_filter = ("status", "is_visible", "course__competition")
    inlines = (SplitInline,)
    actions = (action_hide_results,)


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """FI/EN: Uploaded IOFXML file management."""

    list_display = ("original_name", "competition", "uploaded_at", "size_bytes")
    search_fields = ("original_name", "sha256", "competition__name")
    list_filter = ("competition", "uploaded_at")


@admin.register(Split)
class SplitAdmin(admin.ModelAdmin):
    """FI/EN: Split (intermediate times) management."""

    list_display = ("result", "seq", "control_code", "time_s", "leg_time_s", "note")
    search_fields = (
        "result__athlete__last_name",
        "result__athlete__first_name",
        "result__course__name",
        "control_code",
    )
    list_filter = ("result__course__competition",)


@admin.register(PrivacyPreference)
class PrivacyPreferenceAdmin(admin.ModelAdmin):
    """FI/EN: Per-athlete privacy settings."""

    list_display = (
        "athlete",
        "show_name",
        "hide_until",
        "suppressed_at",
        "consent_basis",
        "retention_until",
    )
    search_fields = ("athlete__last_name", "athlete__first_name", "consent_basis")
    list_filter = ("show_name", "consent_basis", "hide_until", "retention_until")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """FI/EN: Audit log of privacy-related actions."""

    list_display = ("athlete", "event", "by", "at", "data_category", "processing_basis")
    search_fields = ("athlete__last_name", "athlete__first_name", "event", "by")
    list_filter = ("event", "data_category", "processing_basis", "at")
