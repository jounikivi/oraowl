# oraw_app/models/course.py
from __future__ import annotations

import uuid
from django.db import models


class Course(models.Model):
    """
    FI: Rata: nimi, pituus ja viittaus kilpailuun.
    EN: Course: name, length and link to competition.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    competition = models.ForeignKey(
        "oraw_app.Competition",
        on_delete=models.CASCADE,
        related_name="courses",
    )

    # FI: Esim. H21, D18, "Long", "Short".
    # EN: E.g., M21, W18, "Long", "Short".
    name = models.CharField(max_length=100)

    # FI: Pituus kilometreinä; importer konvertoi m -> km.
    # EN: Length in kilometers; importer converts meters -> km.
    length_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Course length in kilometers (optional).",
    )

    climb_m = models.IntegerField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["competition", "name"]
        constraints = [
            # FI: Yksi nimetty rata per kilpailu.
            # EN: One course name per competition.
            models.UniqueConstraint(
                fields=["competition", "name"],
                name="uniq_course_per_competition",
            ),
        ]
        indexes = [
            models.Index(fields=["competition"]),
            models.Index(fields=["name"]),
            models.Index(fields=["length_km"]),
        ]

    def __str__(self) -> str:
        return f"{self.competition.name} / {self.name}"
