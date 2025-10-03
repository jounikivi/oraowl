# tests/test_importer_minimal.py
# FI: Smoke-testi IOF-XML-tuonnille: lue testidata tiedostosta, aja importer,
#     varmista että rivimäärät ja keskeiset arvot täsmäävät.
# EN: Smoke test for IOF XML import: read test data from file, run importer,
#     assert that row counts and key values match.

from pathlib import Path

import pytest
from django.core.management import call_command

from oraw_app.models import (
    Competition,
    Course,
    Athlete,
    Result,
    Split,
    ControlCard,
    UploadedFile,
)


@pytest.mark.django_db
def test_import_minimal_xml_from_file(tmp_path, settings):
    """
    FI: Lue tests/data/results_minimal.xml, tuo se importerilla ja varmista että
        Competition/Course/Athlete/Result/Split/ControlCard syntyvät oikein.
        MEDIA_ROOT ohjataan temp-hakemistoon.
    EN: Read tests/data/results_minimal.xml, import with the command and make sure
        Competition/Course/Athlete/Result/Split/ControlCard are created correctly.
        MEDIA_ROOT is pointed to a temp dir.
    """
    # --- Arrange ------------------------------------------------------
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(media_root)

    # Polku testidatalle (olettaa tiedoston olevan repossa)
    xml_path = Path("tests/data/results_minimal.xml").resolve()
    assert xml_path.exists(), f"Test data not found: {xml_path}"

    # --- Act ----------------------------------------------------------
    call_command("import_iofxml", "--file", str(xml_path))

    # --- Assert: counts -----------------------------------------------
    assert UploadedFile.objects.count() == 1

    assert Competition.objects.count() == 1
    comp = Competition.objects.first()
    assert comp.name
    assert comp.source_file_id is not None

    assert Course.objects.count() == 1
    course = Course.objects.first()
    # FI: 5000 m -> 5.0 km (_length_to_km).
    # EN: 5000 m -> 5.0 km (_length_to_km).
    assert course.length_km == 5.0

    assert Athlete.objects.count() == 1
    ath = Athlete.objects.first()
    assert ath.first_name and ath.last_name

    assert Result.objects.count() == 1
    res = Result.objects.select_related("control_card").first()
    assert res.finish_time_s == 2730
    assert res.status == "OK"
    assert res.position == 1

    assert ControlCard.objects.count() == 1
    card = ControlCard.objects.first()
    assert card.uid == "1234567"
    assert card.vendor == "UNKNOWN"
    assert res.control_card_id == card.id

    assert Split.objects.count() == 3
    codes = list(Split.objects.order_by("seq").values_list("control_code", flat=True))
    assert codes == ["31", "32", "33"]
