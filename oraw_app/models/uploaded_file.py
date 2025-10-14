# oraw_app/models/uploaded_file.py
from __future__ import annotations

import uuid
from django.db import models


class UploadedFile(models.Model):
    """
    FI: Alkuperäiset IOFXML-tiedostot (talletus + deduplikointi sha256:lla).
    EN: Original IOFXML files (storage + sha256-based deduplication).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FI: Fyysinen tiedosto (MEDIA_ROOT / iofxml/...). Säilytä lähde.
    # EN: Actual file on disk (MEDIA_ROOT / iofxml/...).
    stored_file = models.FileField(upload_to="iofxml/%Y/%m/%d")

    # FI: Tiedoston alkuperäinen nimi ja koko (bittimäärä).
    # EN: Original file name and size in bytes.
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()

    # FI: SHA256-tiiviste deduplikointiin (vain uniikit tiedostot).
    # EN: SHA256 hash for deduplication (unique constraint).
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)

    # FI: Latausaika.
    # EN: Upload timestamp.
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # FI: (Valinnainen) lähdeviite (kuka / mistä saatu).
    # EN: (Optional) provenance info (who/where it came from).
    source_name = models.CharField(max_length=120, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # FI: GDPR: auditointikentät (luotu / päivitetty).
    # EN: GDPR: audit fields (created / updated).
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["sha256"]),
        ]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.sha256[:8]}...)"
