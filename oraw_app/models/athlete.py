import uuid
from django.db import models
from django.utils.crypto import get_random_string


def generate_alias() -> str:
    """
    FI: Satunnainen alias julkisiin URL:eihin (ei paljasta ID:tä).
    EN: Random alias for public URLs (prevents leaking the DB ID).
    """
    return get_random_string(10)


class Athlete(models.Model):
    """
    FI: Urheilijan perustiedot (henkilörekisteri, GDPR).
    EN: Athlete’s core personal data (separate registry, GDPR).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    year_of_birth = models.PositiveIntegerField(null=True, blank=True)
    
        # FI: Seura / organisaatio (valinnainen).
    # EN: Club / organisation (optional).
    club = models.CharField(max_length=120, null=True, blank=True)

    # FI: Sukupuoli (M/F/X), valinnainen.
    # EN: Gender (M/F/X), optional.
    GENDER_M = "M"
    GENDER_F = "F"
    GENDER_X = "X"
    GENDER_CHOICES = [
        (GENDER_M, "Male"),
        (GENDER_F, "Female"),
        (GENDER_X, "Other/Unspecified"),
    ]
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
    )


    # FI: Privacy by default → ei julkinen ilman lupaa.
    # EN: Privacy by default → not public unless allowed.
    is_public = models.BooleanField(default=False)

    # FI: Julkinen alias URL:eihin.
    # EN: Public alias for URLs.
    public_alias = models.SlugField(max_length=16, unique=True, default=generate_alias)

    def display_name(self) -> str:
        """
        FI: Palauttaa nimen vain jos julkinen; muuten 'Anonyymi'.
        EN: Returns name only if public; otherwise 'Anonyymi'.
        """
        if not self.is_public:
            return "Anonyymi"
        full = f"{self.first_name} {self.last_name}".strip()
        return full or "Anonyymi"

    def __str__(self) -> str:
        # FI/EN: Admin/debug-friendly representation.
        return self.display_name()


class AthleteIdentifier(models.Model):
    """
    FI: Urheilijan ulkoiset tunnisteet (esim. EMIT/SI, kansallinen ID).
    EN: Athlete’s external identifiers (e.g., EMIT/SI, national ID).
    """

    # FI: N:1 → monta tunnistetta per urheilija.
    # EN: N:1 → many identifiers per athlete.
    athlete = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="identifiers",
    )

    # FI: Tunnisteen tyyppi.
    # EN: Identifier type.
    KIND_CHOICES = [
        ("EMIT", "EMIT"),
        ("SI", "SI"),
        ("NAT", "National ID"),
        ("OTHER", "Other"),
    ]
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)

    # FI: Tunnisteen arvo (numero/merkkijono).
    # EN: Identifier value (number/string).
    value = models.CharField(max_length=64)

    # FI: Onko tämä tunniste aktiivinen.
    # EN: Whether this identifier is active.
    is_active = models.BooleanField(default=True)

    class Meta:
        # FI: Estä duplikaatit samalle urheilijalle.
        # EN: Prevent duplicates for the same athlete.
        constraints = [
            models.UniqueConstraint(
                fields=["athlete", "kind", "value"],
                name="uniq_identifier_per_athlete",
            )
        ]
        # FI: Nopea haku tyypin+arvon mukaan.
        # EN: Fast lookups by type+value.
        indexes = [
            models.Index(fields=["kind", "value"]),
        ]

    def __str__(self) -> str:
        # FI/EN: Compact admin/list display.
        return f"{self.kind}:{self.value}"
