import uuid
from django.db import models

class Course(models.Model):
    """
    FI: Rata (kisan sisällä). Uniikki kisan sisällä nimen perusteella.
    EN: Course within a competition. Unique per competition by name.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    competition = models.ForeignKey(
        "oraw_app.Competition",
        on_delete=models.CASCADE,
        related_name="courses",
    )
    name = models.CharField(max_length=120)
    length_km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # FI: Sarja/luokka (esim. H21, D18).
    # EN: Class/category (e.g., M21, W18).
    clazz = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        ordering = ["competition", "name"]
        constraints = [
            models.UniqueConstraint(fields=["competition", "name"], name="uniq_course_per_competition"),
        ]
        indexes = [
            models.Index(fields=["competition"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.competition}: {self.name}"
