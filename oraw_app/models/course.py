import uuid
from django.db import models


class Course(models.Model):
    """
    FI: Course-malli tallentaa radan perustiedot.
        - UUID pääavaimena turvallisuuden vuoksi.
        - Rata liittyy aina tiettyyn kilpailuun (ForeignKey).
        - Pituus kilometreinä on vapaaehtoinen.
        - Sarjan nimi voi kuvastaa esimerkiksi H21, D18 jne.
    EN: Course model stores the basic information of a course.
        - UUID primary key for security.
        - Course is always linked to a specific competition (ForeignKey).
        - Length in kilometers is optional.
        - Class name may represent categories such as M21, W18, etc.
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link to competition
    competition = models.ForeignKey(
        "oraw_app.Competition",
        on_delete=models.CASCADE,
        related_name="courses",
    )

    # Course/class name (e.g., H21E, D18)
    name = models.CharField(max_length=100)

    # Length in kilometers (optional)
    length_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Creation timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """
        FI: Määrittelee oletusjärjestyksen ja indeksit.
        EN: Defines default ordering and indexes.
        """
        ordering = ["competition", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["competition"]),
        ]

    def __str__(self):
        """
        FI: Mallin tekstiesitys: kilpailun nimi + radan nimi.
        EN: String representation: competition name + course name.
        """
        return f"{self.competition.name} – {self.name}"
