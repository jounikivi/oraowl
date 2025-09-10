import uuid
from django.db import models


class Competition(models.Model):
    """
    FI: Competition-malli tallentaa kilpailun perustiedot.
        - Käytämme UUID-avainta turvallisuuden vuoksi.
        - Nimi, päivämäärä ja sijainti kuvaavat kilpailua.
        - iof_event_id mahdollistaa linkityksen IOFXML-dataan.
    EN: Competition model stores the basic event information.
        - UUID primary key for security.
        - Name, date, and location describe the event.
        - iof_event_id links to IOFXML event data.
    """

    # Primary key: UUID for uniqueness and security
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic fields
    name = models.CharField(max_length=200)
    date = models.DateField()
    location = models.CharField(max_length=200, blank=True)

    # Optional external reference (IOFXML Event ID or similar)
    iof_event_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        help_text="Optional external reference, e.g. IOFXML Event ID",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """
        FI: Järjestää kilpailut oletuksena uusin ensin.
        EN: Orders competitions by newest first.
        """
        ordering = ["-date", "name"]

    def __str__(self):
        """
        FI: Mallin tekstiesitys: kilpailun nimi + päivämäärä.
        EN: String representation: competition name + date.
        """
        return f"{self.name} ({self.date})"
