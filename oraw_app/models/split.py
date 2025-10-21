# oraw_app/models/split.py
# ============================================================
# FI: Väliaikojen (Split) tietomalli.
# EN: Data model for intermediate times (Splits).
# ============================================================

from __future__ import annotations

import uuid
from django.db import models


class Split(models.Model):
    """
    FI: Yksittäinen väliaika (Split) suunnistustuloksessa.
        Jokainen Split kuvaa yhtä rastiväliä tai väliaikaa kilpailun tuloksessa.

    EN: Single split within an orienteering result.
        Each Split represents one control interval or intermediate time.
    """

    # ------------------------------------------------------------
    # 🆔 Primary key
    # ------------------------------------------------------------
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key for split entry",
    )

    # ------------------------------------------------------------
    # 🔗 Relations
    # ------------------------------------------------------------
    result = models.ForeignKey(
        "oraw_app.Result",
        on_delete=models.CASCADE,
        related_name="splits",
        help_text="Link to the parent Result",
    )

    # ------------------------------------------------------------
    # 🔢 Core split data
    # ------------------------------------------------------------
    seq = models.PositiveIntegerField(
        help_text="Sequence number within result, starting from 1"
    )

    control_code = models.CharField(
        max_length=12,
        help_text="Control code (e.g. '31', '100', or special code)",
    )

    split_time_s = models.IntegerField(
        default=0,
        help_text="Leg time (delta from previous split) in seconds",
    )

    cum_time_s = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cumulative time to this control in seconds (optional)",
    )

    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Optional notes or comments for this split",
    )

    # ------------------------------------------------------------
    # 🕒 Audit fields
    # ------------------------------------------------------------
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Creation timestamp (auto set)",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp (auto updated)",
    )

    # ------------------------------------------------------------
    # ⚙️ Model configuration
    # ------------------------------------------------------------
    class Meta:
        db_table = "oraw_app_split"
        verbose_name = "Split"
        verbose_name_plural = "Splits"
        ordering = ["result_id", "seq"]

        indexes = [
            models.Index(fields=["result", "seq"], name="idx_split_result_seq"),
            models.Index(fields=["result", "control_code"], name="idx_split_result_code"),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["result", "seq"],
                name="uniq_split_per_result_seq",
            ),
            models.UniqueConstraint(
                fields=["result", "control_code"],
                name="uniq_split_per_result_code",
            ),
        ]

    # ------------------------------------------------------------
    # 🧠 String representation
    # ------------------------------------------------------------
    def __str__(self) -> str:
        """
        FI: Palauttaa luettavan merkkijonoesityksen.
        EN: Returns a human-readable string representation.
        """
        return (
            f"Result#{self.result_id} seq={self.seq} "
            f"code={self.control_code} "
            f"(split={self.split_time_s}s cum={self.cum_time_s}s)"
        )
