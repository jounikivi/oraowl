# oraw_app/models/competition.py
from __future__ import annotations

import uuid
from django.db import models


class Competition(models.Model):
    """
    FI: Kilpailu: perustiedot + viittaus alkuperäiseen tulostiedostoon.
    EN: Competition: basic data + link to the original results file.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200)
    date = models.DateField(null=True, blank=True)

    organizer = models.CharField(max_length=200, null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)

    # FI: Alkuperäinen IOFXML, josta kilpailu luotiin (jos tiedossa).
    # EN: Original IOFXML used to create this competition (if known).
    source_file = models.ForeignKey(
        "oraw_app.UploadedFile",
        on_delete=models.SET_NULL,
        related_name="competitions_primary",
        null=True,
        blank=True,
        help_text="Original IOFXML file this competition was created from.",
    )

    notes = models.TextField(null=True, blank=True)

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "name"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["organizer"]),
            models.Index(fields=["location"]),
            models.Index(fields=["source_file"]),
        ]

    def __str__(self) -> str:
        when = f" ({self.date})" if self.date else ""
        return f"{self.name}{when}"
