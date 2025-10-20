# oraw_app/models/split.py
from __future__ import annotations

import uuid
from django.db import models


class Split(models.Model):
    """
    FI: Väliaika yhdelle rastille tietyssä tuloksessa.
    EN: One control split for a specific result.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FI: Mihin tulokseen split kuuluu.
    # EN: Parent result this split belongs to.
    result = models.ForeignKey(
        "oraw_app.Result",
        on_delete=models.CASCADE,
        related_name="splits",
    )

    # FI: Rastikoodi (esim. "31") kuten IOF XML:ssä.
    # EN: Control code (e.g., "31") as in IOF XML.
    control_code = models.CharField(max_length=12)

    # FI: Järjestysnumero reitillä, alkaa 1:stä.
    # EN: Sequential order in the course, starting from 1.
    seq = models.PositiveIntegerField()

    # FI: Tähän rastiväliin käytetty aika sekunneissa.
    # EN: Leg time (split) in seconds.
    split_time_s = models.IntegerField()

    # FI: Kumulatiivinen aika maaliin asti (jos lähteessä annettu).
    # EN: Cumulative elapsed time (if provided by source).
    cum_time_s = models.IntegerField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["result", "seq"]
        constraints = [
            # FI: Yksi seq per result.
            # EN: One seq per result.
            models.UniqueConstraint(
                fields=["result", "seq"],
                name="uniq_split_per_result_seq",
            ),
            # FI: Yksi rastikoodi per result (jos koodi toistuu, poista tämä).
            # EN: One control code per result (drop if codes can repeat).
            models.UniqueConstraint(
                fields=["result", "control_code"],
                name="uniq_split_per_result_code",
            ),
        ]
        indexes = [
            models.Index(fields=["result"]),
            models.Index(fields=["control_code"]),
            models.Index(fields=["seq"]),
        ]

    def __str__(self) -> str:
        return f"{self.result_id}#{self.seq} ({self.control_code})"
