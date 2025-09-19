import uuid
from django.db import models

class UploadedFile(models.Model):
    """
    FI: Alkuperäiset IOFXML-tiedostot (deduplikointi + lähde + re-prosessointi).
    EN: Original IOFXML files (dedup + provenance + re-processing).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    competition = models.ForeignKey(
        "oraw_app.Competition",
        on_delete=models.CASCADE,
        related_name="uploads",
        help_text="The competition this file belongs to.",
    )

    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    # FI: Lähdeviite helpottaa osoitusvelvollisuutta.
    # EN: Provenance helps GDPR accountability.
    source_name = models.CharField(max_length=120, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["competition"]),
        ]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.sha256[:8]}...)"
