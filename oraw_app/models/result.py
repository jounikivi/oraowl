import uuid
from django.db import models


class Result(models.Model):
    """
    FI: Urheilijan tulos tietyllä radalla. Näkyvyys ja soft delete GDPR:ää varten.
    EN: An athlete's result on a specific course. Visibility & soft delete for GDPR.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    athlete = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="results",
    )
    course = models.ForeignKey(
        "oraw_app.Course",
        on_delete=models.CASCADE,
        related_name="results",
    )

    # FI: Kokonaisaika sekunteina; IOFXML parsitaan tallennettaessa.
    # EN: Finish time in seconds; populated by IOFXML parser.
    finish_time_s = models.PositiveIntegerField(null=True, blank=True)

    # FI: Tilan koodi: OK, DSQ (hylätty), DNS (ei startannut) jne.
    # EN: Status code.
    STATUS_CHOICES = [
        ("OK", "OK"),
        ("DSQ", "Disqualified"),
        ("DNS", "DidNotStart"),
        ("DNF", "DidNotFinish"),
        ("MP", "MissingPunch"),
        ("UNK", "Unknown"),
    ]
    status = models.CharField(
        max_length=8,
        choices=STATUS_CHOICES,
        default="UNK",
    )

    # FI: Johdettu: sekuntia / km, voi tallentaa analyysin nopeuttamiseksi.
    # EN: Derived: seconds per km; optional cache for faster analytics.
    pace_s_per_km = models.PositiveIntegerField(null=True, blank=True)

    # FI: Sijoitus (valinnainen jos puuttuu lähteestä).
    # EN: Position/ranking if available.
    position = models.PositiveIntegerField(null=True, blank=True)

    # FI: Näkyvyys ja soft delete (GDPR).
    # EN: Visibility & soft delete (GDPR).
    is_visible = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ["finish_time_s", "athlete__last_name", "athlete__first_name"]
        constraints = [
            # One result per (course, athlete); add attempt_no if you need multiples
            models.UniqueConstraint(
                fields=["course", "athlete"],
                name="uniq_result_per_course_athlete",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["pace_s_per_km"]),
            models.Index(fields=["course", "athlete"]),
            models.Index(fields=["is_visible"]),
            models.Index(fields=["deleted_at"]),
        ]

    def __str__(self) -> str:
        return f"Result({self.athlete} @ {self.course})"
