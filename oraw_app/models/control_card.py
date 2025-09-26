# oraw_app/models/control_card.py
from __future__ import annotations

import uuid
from django.db import models


class ControlCard(models.Model):
    """
    FI: Leimauskortti (Emit, SI, tms.). Uniikki valmistaja + tunniste.
    EN: Control card (Emit, SI, etc.). Unique vendor + uid together.
    """

    EMIT = "EMIT"
    SI = "SI"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

    VENDOR_CHOICES = [
        (EMIT, "Emit"),
        (SI, "SportIdent"),
        (OTHER, "Other"),
        (UNKNOWN, "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.CharField(max_length=16, choices=VENDOR_CHOICES, default=UNKNOWN)
    uid = models.CharField(max_length=64)  # valmistajakohtainen id (string, jotta joustava)

    notes = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        ordering = ["vendor", "uid"]
        constraints = [
            # FI: Yksi rivi per (vendor, uid)
            # EN: Uniqueness per (vendor, uid)
            models.UniqueConstraint(fields=["vendor", "uid"], name="uniq_controlcard_vendor_uid"),
        ]
        indexes = [
            models.Index(fields=["vendor", "uid"]),
        ]

    def __str__(self) -> str:
        return f"{self.vendor}:{self.uid}"
