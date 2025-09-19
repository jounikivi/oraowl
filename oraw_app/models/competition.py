import uuid
from django.db import models


class Competition(models.Model):
    """
    FI: Kilpailun perustiedot. Lähdetieto (source) helpottaa osoitusvelvollisuutta.
    EN: Core competition data. Source fields aid GDPR accountability.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=160)
    date = models.DateField(null=True, blank=True)
    organizer = models.CharField(max_length=160, null=True, blank=True)
    location = models.CharField(max_length=160, null=True, blank=True)

    # FI: (Valinnainen) IOF:n event-id, jos lähteessä on.
    # EN: Optional IOF event id if present in source.
    iof_event_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    # FI: Läpinäkyvyys/lähdeviite.
    # EN: Transparency / provenance.
    source_name = models.CharField(max_length=120, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "date"],
                name="uniq_competition_name_date",
            ),
        ]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.date})" if self.date else self.name
