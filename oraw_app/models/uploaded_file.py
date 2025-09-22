# oraw_app/models/uploaded_file.py
import uuid
from django.db import models


class UploadedFile(models.Model):
    """
    FI: Alkuperäiset IOFXML-tiedostot (talletus + deduplikointi sha256:lla).
    EN: Original IOFXML files (persist + sha256-based deduplication).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FI: Fyysinen tiedosto (MEDIA_ROOT / iofxml/...). Säilytä lähde.
    # EN: Actual file on disk (MEDIA_ROOT / iofxml/...).
    stored_file = models.FileField(upload_to="iofxml/%Y/%m/%d")

    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    # FI: (Valinn.) Lähdeviite (kuka/ mistä saatu).
    # EN: (Optional) Provenance info.
    source_name = models.CharField(max_length=120, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["sha256"]),
            
        ]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.sha256[:8]}...)"
