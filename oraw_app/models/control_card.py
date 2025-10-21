# oraw_app/models/control_card.py
from __future__ import annotations

import uuid
from django.db import models


class ControlCard(models.Model):
    """
    FI: Leimauskortti (Emit/SI/...). Yksi fyysinen kortti yksilöityy
        valmistajan tunnisteella (vendor) ja kortin UID:lla.
        Sama kortti voi esiintyä usean urheilijan tuloksissa eri kilpailuissa.
    EN: Control card (Emit/SI/...). A physical card is identified by the
        vendor and the card UID. The same card can appear in results of
        multiple athletes across different competitions.
    """

    VENDOR_UNKNOWN = "UNKNOWN"
    VENDOR_EMIT = "EMIT"
    VENDOR_SI = "SI"
    VENDOR_OTHER = "OTHER"

    VENDOR_CHOICES = [
        (VENDOR_UNKNOWN, "UNKNOWN"),
        (VENDOR_EMIT, "EMIT"),
        (VENDOR_SI, "SI"),
        (VENDOR_OTHER, "OTHER"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vendor = models.CharField(
        max_length=16,
        choices=VENDOR_CHOICES,
        default=VENDOR_UNKNOWN,
        help_text="Card vendor/manufacturer.",
    )

    # FI: Valmistajan yksilöllinen tunniste. Esim. numero tai heksamerkkijono.
    # EN: Manufacturer-specific unique identifier. E.g. number or hex string.
    uid = models.CharField(max_length=64)

    # FI: (Valinnainen) omistaja viitteellinen. Korttia voi käyttää muutkin
    # kilpailussa, joten tämä ei rajoita käyttöä.
    # EN: (Optional) nominal owner reference. The card can still be used
    # by others in competitions; this does not restrict usage.
    owner = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.SET_NULL,
        related_name="control_cards",
        null=True,
        blank=True,
    )

    notes = models.TextField(null=True, blank=True)

    # FI: Audit-aikaleimat.
    # EN: Audit timestamps.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vendor", "uid"]
        constraints = [
            # FI: Sama kortti saa esiintyä tietokannassa vain kerran (vendor+uid).
            # EN: Ensure a single physical card (vendor+uid) is unique.
            models.UniqueConstraint(
                fields=["vendor", "uid"],
                name="uniq_control_card_vendor_uid",
            ),
        ]
        indexes = [
            models.Index(fields=["vendor"]),
            models.Index(fields=["uid"]),
        ]

    def __str__(self) -> str:
        return f"{self.vendor}:{self.uid}"
