from django.conf import settings
from django.db import connection

def test_secret_key_present():
    assert bool(settings.SECRET_KEY)

def test_db_available(db):
    # db-fixture luo tyhjän testitietokannan pytest-djangossa
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
