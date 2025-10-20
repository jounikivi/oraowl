# oraw_app/models/split.py
from __future__ import annotations

from django.db import models


class Split(models.Model):
    """
    FI: Väliaika/ rastiväli yhdelle tulokselle (Result). Sisältää sekä väliajan että
        kumulatiivisen ajan, sekä rastikoodin ja järjestysnumeron.
    EN: Intermediate split for a single Result. Holds both split (leg) time and
        cumulative time, plus control code and sequence number.
    """

    # --- Relations -----------------------------------------------------
    # FI: Tulokseen liittyvä FK. related_name="splits" helpottaa käänteishakua (result.splits.all()).
    # EN: Link to Result; related_name makes reverse lookup convenient (result.splits.all()).
    result = models.ForeignKey(
        "oraw_app.Result",
        on_delete=models.CASCADE,
        related_name="splits",
    )

    # --- Core data -----------------------------------------------------
    # FI: Järjestysnumero (1, 2, 3, ...), eli monesko väli.
    # EN: Sequence number (1, 2, 3, ...), i.e., which leg number this is.
    seq = models.PositiveIntegerField()

    # FI: Rastin koodi (esim. "31"). Ei tyhjäksi.
    # EN: Control code (e.g., "31"). Not nullable.
    control_code = models.CharField(max_length=12)

    # FI: Väliaika sekunteina (tämän välin kesto). Pidä aina kokonaislukuna.
    # EN: Split (leg) time in seconds for this leg. Always integer seconds.
    split_time_s = models.IntegerField(default=0)

    # FI: Kumulatiivinen aika sekunteina tähän väliin asti. Saa olla tyhjä.
    # EN: Cumulative time in seconds up to this leg. Optional.
    cum_time_s = models.IntegerField(null=True, blank=True)

    # --- Meta / misc ---------------------------------------------------
    # FI: Vapaa muistiinpano.
    # EN: Free-form notes.
    notes = models.TextField(null=True, blank=True)

    # FI: Auditointi.
    # EN: Auditing.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # FI: Järjestys: tulos ja järjestysnumero.
        # EN: Default ordering: by result then sequence.
        ordering = ["result", "seq"]

        # FI: Tietokantatason uniikkius—yksi rivi/ (result, seq) ja yksi rivi/ (result, control_code).
        # EN: DB-level uniqueness—one row per (result, seq) and per (result, control_code).
        constraints = [
            models.UniqueConstraint(
                fields=["result", "seq"], name="uniq_split_per_result_seq"
            ),
            models.UniqueConstraint(
                fields=["result", "control_code"], name="uniq_split_per_result_code"
            ),
        ]

        # FI: Hyödylliset indeksit hakuihin.
        # EN: Helpful indexes for common queries.
        indexes = [
            models.Index(fields=["result", "seq"]),
            models.Index(fields=["result", "control_code"]),
        ]

    def __str__(self) -> str:
        # FI: esim. "Result#123 seq=3 code=31 (split=600s cum=2000s)"
        # EN: e.g. "Result#123 seq=3 code=31 (split=600s cum=2000s)"
        return (
            f"Result#{getattr(self.result, 'id', '?')} "
            f"seq={self.seq} code={self.control_code} "
            f"(split={self.split_time_s}s cum={self.cum_time_s}s)"
        )
