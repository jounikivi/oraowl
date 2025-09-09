from django.db import models

class PrivacyPreference(models.Model):
  
   athlete = models.OneToOneField(
     "oraw_app.Athlete",
     on_delete=models.CASCADE,
     related_name="privacy"     
    )
   
   # FI: Sallitaanko nimen näyttäminen? Oletus False = ei näytetä.
   # # EN: Allow showing the name? Default False = hidden.
   show_name = models.BooleanField(default=False)
   
    # FI: Piilota nimeä määräaikaisesti tähän päivään asti.
    # EN: Hide the name until this date (optional)
   hide_until =models.DateField(null=True, blank=True)
   
    # FI: Adminin tekemä “piilotettu” -aikaleima.
    # EN: Timestamp when an admin has suppressed visibility
   suppressed_at = models.DateTimeField(null=True, blank=True)
   
   def __str__(self) -> str:
    # FI: Adminin tekemä “piilotettu” -aikaleima.
    # EN: Timestamp when an admin has suppressed visibility
    return f"PrivacyPreference({self.athlete_id})"
  
class AuditLog(models.Model):
  """
    FI: Yksinkertainen loki tietosuojatoimille (kuka, mitä, milloin, miksi).
    EN: Simple audit log for privacy actions (who, what, when, why).
    """
  
  #FI: mahdollistaa athlete.privacy; 
  #EN: access via athlete.privacy  
  athlete = models.ForeignKey(
    "oraw_app.Athlete",
    on_delete=models.CASCADE,
    related_name="privacy_audit_logs" 
  )
  
  # FI: Tapahtuman tyyppi (esim. 'hide', 'show', 'anonymize').
  # EN: Event type (e.g. 'hide', 'show', 'anonymize').
  event = models.CharField(max_length=200)
  
  # FI: Selitys, miksi muutos tehtiin (voi olla tyhjä).
  # EN: Reason why the change was made (optional).
  reason = models.TextField(null=True, blank=True)
  
   # FI: Aikaleima, milloin lokimerkintä luotiin (automaattisesti).
  # EN: Timestamp when the log entry was created (set automatically)
  at = models.DateTimeField(auto_now_add=True)
  
  # FI: Kuka teki muutoksen (esim. adminin käyttäjänimi tai sähköposti).
  # EN: Who performed the change (e.g. admin username or email)
  by = models.CharField(max_length=200)
  
  def __str__(self):
   # FI: Ytimekäs esitys adminissa ja lokituksessa.
   # EN: Concise representation in admin and logging.
   return f"{self.event} for Athlete({self.athlete_id}) at {self.at}"
  
  
    
