import uuid
from django.db import models

class Result(models.Model):
    """
    FI: Result-malli tallentaa urheilijan suorituksen tietyllä radalla.
        - UUID pääavaimena turvallisuuden vuoksi.
        - Viittaus Courseen (rata) ja Athleteen (henkilörekisteri).
        - Aika sekunteina ja (valinnainen) vauhti s/km.
        - Status (OK, DNF, DSQ, MP, DNS) kuvaa suorituksen tilaa.
    EN: Result model stores an athlete's performance on a course.
        - UUID primary key for security.
        - References Course (track) and Athlete (personal register).
        - Finish time in seconds and optional pace (s/km).
        - Status (OK, DNF, DSQ, MP, DNS) describes the outcome.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Realtions
    course = models.ForeignKey(
      'oraw_app.Course',
      on_delete=models.CASCADE,
      related_name='results',
      help_text="The course this result belongs to"
    )
    
    # FI: PROTECT estää henkilön poistamisen, jos tuloksia on.
    # EN: PROTECT prevents deleting a person if results exist.
    athlete = models.ForeignKey(
      'oraw_app.Athlete',
      on_delete=models.PROTECT,
      related_name='results',
      help_text="The athlete this result belongs to"
    )
    
    # Timing
    # FI: Maaliaika sekunteina (helpottaa laskentaa).
    # EN: Finish time in seconds (easier for computation).
    finish_time_s = models.PositiveIntegerField(null=True, blank=True)
    
    # FI: Vauhti sekuntia per kilometri (johdettu arvo, vapaaehtoinen).
    # EN: Pace in seconds per kilometer (derived, optional)
    pace_s_per_km = models.PositiveIntegerField(null=True, blank=True)
    
    # FI: Suorituksen tila (OK, DNF, DSQ, MP, DNS).
    # EN: Status of the performance (OK, DNF, DSQ, MP, DNS).
    STATUS_OK = 'OK'
    STATUS_DNF = 'DNF'
    STATUS_DSQ = 'DSQ'
    STATUS_MP = 'MP'
    STATUS_DNS = 'DNS'
    STATUS_CHOICES = [
        ('OK', 'OK'),
        ('DNF', 'Did Not Finish'),
        ('DSQ', 'Disqualified'),
        ('MP', 'Missing Punches'),
        ('DNS', 'Did Not Start'),
    ]
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    
    # Misc
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
      """
      FI: Indeksit hakua ja listauksia varten (status, vauhti, yhdistelmät).
      EN: Indexes for lookups and listings (status, pace, combinations).
      
      """
      
      indexes = [
          models.Index(fields=['status']),
          models.Index(fields=['pace_s_per_km']),
          models.Index(fields=['course', 'athlete']),
      ]
      
      # FI: Tuoreimmat ensin toimii usein listauksissa luontevasti.
      # EN: Newest first is convenient in listings.
      ordering = ['finish_time_s', 'athlete__last_name', 'athlete__first_name']
      
      def __str__(self) -> str:
        """
        FI: Tekstiesitys: Athleten näyttönimi + rata.
        EN: String representation: athlete display name + course.
        """
        return f"Result({self.athlete} @ {self.course})"
