# oraw_app/models/result.py
from __future__ import annotations

import uuid
from django.db import models


class Result(models.Model):
    """
    FI: Yksittäinen kilpailutulos. Yksi virallinen tulos / urheilija / rata.
    EN: Single competition result. One official result per athlete per course.
    """

    STATUS_OK = "OK"
    STATUS_DNF = "DNF"
    STATUS_DSQ = "DSQ"
    STATUS_MP = "MP"
    STATUS_OTHER = "OTHER"

    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_DNF, "Did not finish"),
        (STATUS_DSQ, "Disqualified"),
        (STATUS_MP, "Missing punch"),
        (STATUS_OTHER, "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        "oraw_app.Course",
        on_delete=models.CASCADE,
        related_name="results",
    )
    athlete = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="results",
    )

    # FI: Leimauskortti, jos tiedossa (Emit/SI/..). Ei pakollinen.
    # EN: Control card used, if known (Emit/SI/..). Optional.
    control_card = models.ForeignKey(
        "oraw_app.ControlCard",
        on_delete=models.SET_NULL,
        related_name="results",
        null=True,
        blank=True,
    )

    # FI: Aika sekunteina (kokonaisaika). Voi puuttua, jos DSQ tms.
    # EN: Finish time in seconds. May be null for DSQ, etc.
    finish_time_s = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_OK
    )

    # FI: Sijoitus (1, 2, 3, ...), jos tiedossa.
    # EN: Finishing position (1, 2, 3, ...), if known.
    position = models.PositiveIntegerField(null=True, blank=True)

    # FI: Keskivauhti s/km. Lasketaan erikseen, voi puuttua.
    # EN: Pace seconds per km. Calculated elsewhere, may be null.
    pace_s_per_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    # FI: Julkisuus ja pehmeä poisto (GDPR).
    # EN: Public visibility and soft delete (GDPR).
    is_public = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # FI: Raportoinnissa tyypillinen lajittelu: kilpailu/rata → sijoitus.
        # EN: Common reporting order: competition/course → position.
        ordering = ["course__competition", "course__name", "position"]
        constraints = [
            # FI: Yksi virallinen tulos / urheilija / rata.
            # EN: One official result per athlete per course.
            models.UniqueConstraint(
                fields=["course", "athlete"],
                name="uniq_result_per_course_athlete",
            ),
        ]
        indexes = [
            models.Index(fields=["course"]),
            models.Index(fields=["athlete"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["deleted_at"]),
            models.Index(fields=["pace_s_per_km"]),
        ]
        
    @property
    def finish_time_hms(self) -> str:
        """
        FI: Palauttaa kokonaisajan muodossa H:MM:SS.
            Jos aikaa ei ole (esim. DSQ), palauttaa '-'.
        EN: Returns finish time in H:MM:SS format.
            Returns '-' if time is missing (e.g. DSQ).
        """
        if self.finish_time_s is None:
            return "-"

        total_seconds = int(self.finish_time_s)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:d}:{minutes:02d}:{seconds:02d}"


    def __str__(self) -> str:
        athlete = getattr(self.athlete, "display_name", lambda: "Athlete")()
        course = getattr(self.course, "name", "Course")
        return f"{athlete} @ {course} [{self.status}]"
