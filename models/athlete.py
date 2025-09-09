import uuid
from django.db import models
from django.utils.crypto import get_random_string

def generate_alias() -> str:
    # FI: Luo satunnaisen merkkijonon urheilijan julkiseen URL-osoitteeseen
    # EN: Generate a random string for athlete's public URL
    return get_random_string(10)

class Athlete(models.Model):
    # FI: Käytetään UUID:ta tietoturvan vuoksi (ei peräkkäisiä ID-arvoja)
    # EN: UUID primary key for better security
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FI: Nimi ja syntymävuosi, mutta voidaan piilottaa jos henkilö pyytää
    # EN: Name and year of birth, can be hidden for privacy
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    year_of_birth = models.PositiveIntegerField(null=True, blank=True)

    # FI: Oletusarvoisesti urheilijan tiedot eivät ole julkisia (GDPR: Privacy by Default)
    # EN: By default, athlete data is not public (GDPR: Privacy by Default)
    is_public = models.BooleanField(default=False)

    # FI: Julkinen alias (satunnainen tunniste), käytetään URL:eissa
    # EN: Public alias (random slug), used in URLs instead of database ID
    public_alias = models.SlugField(max_length=16, unique=True, default=generate_alias)

    def display_name(self) -> str:
        # FI: Palauttaa "Anonyymi", jos tietoja ei saa näyttää
        # EN: Returns "Anonyymi" if athlete data is hidden
        if not self.is_public:
            return "Anonyymi"
        full = f"{self.first_name} {self.last_name}".strip()
        return full or "Anonyymi"

    def __str__(self):
        # FI: Näytetään adminissa ja debuggauksessa
        # EN: Displayed in admin and debugging
        return self.display_name()
    
class AthleteIdentifier(models.Model):
    """
    FI: Ulkoiset tunnisteet urheilijalle (esim. EMIT/SI-kortti, kansallinen ID).
    EN: External identifiers for an athlete (e.g., EMIT/SI card, national ID).
    """
