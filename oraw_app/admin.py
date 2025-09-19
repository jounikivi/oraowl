# oraw_app/admin.py
"""
FI: Admin jätetään väliaikaisesti tyhjäksi, kunnes uudet mallit ovat valmiit.
EN: Keep admin empty for now; register new models after they exist.
"""
from django.contrib import admin
from .models import Athlete, PrivacyPreference, AuditLog


# Register your models here.
@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("public_alias", "first_name", "last_name", "is_public")
    search_fields = ("public_alias", "first_name", "last_name")
    list_filter = ("is_public",)


@admin.register(PrivacyPreference)
class PrivacyPreferenceAdmin(admin.ModelAdmin):
    list_display = ("athlete", "show_name", "hide_until", "suppressed_at")
    list_filter = ("show_name",)
    search_fields = ("athlete__first_name", "athlete__last_name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("athlete", "event", "by", "at")
    list_filter = ("event", "by")
    search_fields = ("athlete__first_name", "athlete__last_name", "by", "reason")
