# oraw_app/models/athlete.py
from __future__ import annotations

import uuid
import secrets
import string
from django.db import models


def generate_alias(length: int = 16) -> str:
    """
    FI: Historiallisen migraation käyttämä oletusarvo alias-kentälle.
        Palauttaa lyhyen 'anon-xxxxx' -merkkijonon (max length 16).
    EN: Default generator used by old migration for alias field.
        Returns a short 'anon-xxxxx' string (max length 16).
    """
    prefix = "anon-"
    rand_len = max(4, length - len(prefix))
    alphabet = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(rand_len))
    return (prefix + suffix)[:length]


class Athlete(models.Model):
    """
    FI: Urheilija (henkilötiedot minimissä). GDPR:lle tuki anonymisointiin.
    EN: Athlete (minimal PII). Supports GDPR-friendly anonymization.
    """

    GENDER_M = "M"
    GENDER_F = "F"
    GENDER_X = "X"
    GENDER_CHOICES = [
        (GENDER_M, "Male"),
        (GENDER_F, "Female"),
        (GENDER_X, "Other/Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=120, blank=True, default="")
    club = models.CharField(max_length=120, null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, null=True, blank=True
    )
    year_of_birth = models.PositiveIntegerField(null=True, blank=True)

    # FI: Julkisuus ja vaihtoehtoinen julkinen nimi (alias).
    # EN: Public visibility and optional public alias.
    is_public = models.BooleanField(default=True)
    public_alias = models.CharField(max_length=120, null=True, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Helpers -----------------------------------------------------

    def display_name(self) -> str:
        """
        FI: Jos ei julkinen, näytä alias (tai 'Anonyymi' varalla).
        EN: If not public, show alias (or 'Anonyymi' fallback).
        """
        if not self.is_public:
            return self.public_alias or "Anonyymi"
        full = f"{self.first_name} {self.last_name}".strip()
        return full or "Anonyymi"

    def __str__(self) -> str:
        return self.display_name()

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["club"]),
            models.Index(fields=["gender"]),
        ]


class AthleteIdentifier(models.Model):
    """
    FI: Ulkoiset tunnisteet (esim. lisenssi, fed-id). Ei pakollisia.
    EN: External identifiers (e.g., license, federation id). Optional.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        Athlete,
        on_delete=models.CASCADE,
        related_name="identifiers",
    )
    kind = models.CharField(max_length=30)  # e.g. "license", "fed_id"
    value = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["athlete", "kind", "value"],
                name="uniq_identifier_per_athlete",
            ),
        ]
        indexes = [
            models.Index(fields=["athlete", "kind"]),
            models.Index(fields=["value"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.value}"
