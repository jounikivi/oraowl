# oraw_app/models/privacy.py
from __future__ import annotations

import uuid
from django.db import models


class PrivacyPreference(models.Model):
    """
    FI: Henkilötietojen käsittelyyn liittyvät asetukset ja pyynnöt (GDPR).
    EN: Data protection preferences and requests (GDPR).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FI: Käyttäjä/henkilö johon asetus liittyy (Athlete).
    # EN: The person this preference is about (Athlete).
    athlete = models.OneToOneField(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="privacy",
    )

    # FI: Näytetäänkö urheilijan nimi julkisesti (testi odottaa tätä kenttää).
    # EN: Whether athlete's name is shown publicly (test expects this field).
    show_name = models.BooleanField(default=True)

    # FI: Käsittelyn oikeusperuste (esim. oikeutettu etu, suostumus).
    # EN: Legal basis for processing (e.g., legitimate interest, consent).
    consent_basis = models.CharField(
        max_length=50,
        default="legitimate_interest",
    )

    # FI: Rekisteröidyn pyyntö (esim. tarkastus, poisto).
    # EN: Data subject request (e.g., access, erasure).
    data_subject_request_at = models.DateTimeField(null=True, blank=True)
    data_subject_request_type = models.CharField(
        max_length=32,
        null=True,
        blank=True,  # e.g. "access", "erasure", "rectification"
    )
    data_subject_request_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,  # e.g. "pending", "done", "rejected"
    )

    # FI: Henkilötietojen säilytysaika (poistettavissa tämän jälkeen).
    # EN: Personal data retention limit (eligible for deletion after this).
    retention_until = models.DateField(null=True, blank=True)

    # FI: Lisäselite: tietoryhmä ja käsittelyn perusta (raportointia varten).
    # EN: Extra context: data category and basis (for reporting).
    data_category = models.CharField(
        max_length=64,
        null=True,
        blank=True,  # e.g. "identity", "performance"
    )
    processing_basis = models.CharField(
        max_length=50,
        null=True,
        blank=True,  # e.g. "legitimate_interest", "consent"
    )

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["athlete"]
        indexes = [
            models.Index(fields=["show_name"]),
            models.Index(fields=["retention_until"]),
            models.Index(fields=["data_subject_request_status"]),
        ]

    def __str__(self) -> str:
        return f"PrivacyPreference({self.athlete_id})"


class AuditLog(models.Model):
    """
    FI: Yksinkertainen audit-loki (kuka/mikä muuttui ja milloin).
    EN: Simple audit log (who/what changed and when).
    """

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_ACCESS = "ACCESS"

    ACTION_CHOICES = [
        (ACTION_CREATE, "CREATE"),
        (ACTION_UPDATE, "UPDATE"),
        (ACTION_DELETE, "DELETE"),
        (ACTION_ACCESS, "ACCESS"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    athlete = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.SET_NULL,
        related_name="privacy_audit_logs",
        null=True,
        blank=True,
    )

    # FI: Yhteensopivuus testin kanssa: 'event' ja 'by'.
    # EN: Test compatibility: 'event' and 'by'.
    event = models.CharField(max_length=64, null=True, blank=True)
    by = models.CharField(max_length=64, null=True, blank=True)

    # FI: Toimintatyyppi (jos käytetään sisäisesti).
    # EN: Action type (if used internally).
    action = models.CharField(max_length=12, choices=ACTION_CHOICES, null=True, blank=True)

    at = models.DateTimeField(auto_now_add=True)

    # FI: Lyhyt selite ja vapaa muistiinpano (vältä PII).
    # EN: Short description and free-form note (avoid PII).
    description = models.CharField(max_length=200, null=True, blank=True)
    details = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-at"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["at"]),
            models.Index(fields=["event"]),
            models.Index(fields=["by"]),
        ]

    def __str__(self) -> str:
        who = self.athlete_id or "-"
        # Näytä mieluummin event kuin action, jos saatavilla.
        tag = self.event or self.action or "-"
        return f"{tag} @ {self.at:%Y-%m-%d %H:%M:%S} (athlete={who})"

