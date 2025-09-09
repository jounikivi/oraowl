import pytest
from oraw_app.models import Athlete, PrivacyPreference, AuditLog

@pytest.mark.django_db
def test_privacy_preference_defaults_and_relations():
    a = Athlete.objects.create(is_public=False)
    pref = PrivacyPreference.objects.create(athlete=a, show_name=False)
    assert a.privacy == pref
    log = AuditLog.objects.create(athlete=a, event="hide", by="admin")
    assert log.athlete == a
    assert a.privacy_audit_logs.count() == 1
    
    
