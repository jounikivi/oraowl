from django.db import models


class PrivacyPreference(models.Model):
    """
    FI: Henkilökohtaiset tietosuoja-asetukset / pyyntöjen seuranta.
    EN: Per-athlete privacy settings / subject request tracking.
    """

    athlete = models.OneToOneField(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="privacy",
    )

    # FI: Saako nimeä näyttää julkisesti?
    # EN: May we show the real name publicly?
    show_name = models.BooleanField(default=False)

    # FI: Piilotuksen aikaraja (esim. kilpailukauden loppuun).
    # EN: Optional hide-until date.
    hide_until = models.DateField(null=True, blank=True)

    # FI: Adminin suorittama näkyvyyden eston aikaleima.
    # EN: Timestamp when admin suppressed visibility.
    suppressed_at = models.DateTimeField(null=True, blank=True)

    # FI: Oikeusperuste / pyyntöjen seuranta / säilytys.
    # EN: Legal basis / DSR tracking / retention.
    consent_basis = models.CharField(
        max_length=50,
        default="legitimate_interest",
    )
    data_subject_request_at = models.DateTimeField(null=True, blank=True)

    # access | erasure | rectification | restriction
    data_subject_request_type = models.CharField(
        max_length=32,
        null=True,
        blank=True,
    )

    # pending | done | rejected
    data_subject_request_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    retention_until = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"PrivacyPreference({self.athlete_id})"


class AuditLog(models.Model):
    """
    FI: Yksinkertainen audit-loki tietosuojatoimille (kuka, mitä, milloin, miksi).
    EN: Simple audit log for privacy actions (who, what, when, why).
    """

    athlete = models.ForeignKey(
        "oraw_app.Athlete",
        on_delete=models.CASCADE,
        related_name="privacy_audit_logs",
    )
    event = models.CharField(max_length=200)
    reason = models.TextField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)
    by = models.CharField(max_length=200)

    # data_category: identity | performance | contact
    data_category = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )
    # processing_basis: legitimate_interest | consent | public_record
    processing_basis = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-at"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event} for Athlete({self.athlete_id}) at {self.at}"
