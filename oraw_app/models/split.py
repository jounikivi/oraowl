import uuid
from django.db import models

class Split(models.Model):
    """
    FI: Väliajat (SplitTimes) tulokselle. Tallennus sekunteina analytiikkaa varten.
    EN: Per-control intermediate times for a Result. Stored as seconds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    result = models.ForeignKey(
        "oraw_app.Result",
        on_delete=models.CASCADE,
        related_name="splits",
        help_text="Parent result this split belongs to.",
    )

    # FI: Järjestysnumero radalla ja (valinn.) rastikoodi.
    # EN: Sequence in course (1-based) and optional control code.
    seq = models.PositiveIntegerField(help_text="1-based order of the control in the course.")
    control_code = models.CharField(max_length=16, null=True, blank=True)

    # FI: Kumulatiivinen aika ja välin aika (sekunteina).
    # EN: Cumulative time and leg time (seconds).
    time_s = models.PositiveIntegerField(help_text="Cumulative time in seconds since start.")
    leg_time_s = models.PositiveIntegerField(help_text="Leg time in seconds from previous split.")

    # FI: Huomiot (esim. MP-riski tms.).
    # EN: Notes/flags if parser detects issues.
    note = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        ordering = ["result", "seq"]
        constraints = [
            models.UniqueConstraint(fields=["result", "seq"], name="uniq_split_result_seq"),
        ]
        indexes = [
            models.Index(fields=["result"]),
            models.Index(fields=["seq"]),
            models.Index(fields=["control_code"]),
        ]

    def __str__(self) -> str:
        return f"Split(seq={self.seq}, t={self.time_s}s)"
