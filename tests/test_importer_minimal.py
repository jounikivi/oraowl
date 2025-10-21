# tests/test_importer_minimal.py
# FI: Smoke-testi IOF-XML-tuonnille: luo pieni XML, aja importer, varmista rivimäärät.
# EN: Smoke test for IOF XML import: create small XML, run importer, assert row counts.

import textwrap


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
def test_import_minimal_xml(tmp_path, settings):
    # --- Arrange ------------------------------------------------------
    # FI: MEDIA_ROOT ohjataan tilapäiskansioon, jotta FileField kirjoittaa testiin.
    # EN: Point MEDIA_ROOT to a temp dir so FileField writes into test sandbox.
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(media_root)

    # FI: Pieni IOF v3 XML, joka sopii meidän importerille (child-elementit, ei attribuuttimuotoa).
    # EN: Small IOF v3 XML compatible with our importer (child elements, not attribute-only).
    xml_text = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <ResultList xmlns="http://www.orienteering.org/datastandard/3.0" iofVersion="3.0">
          <Event>
            <Name>Test Event</Name>
            <StartTime><Date>2025-01-01</Date></StartTime>
            <Organizer><Name>Test Club</Name></Organizer>
            <Place>Helsinki</Place>
          </Event>

          <ClassResult>
            <Class><Name>H21</Name></Class>
            <Course>
              <Length unit="m">5000</Length>
            </Course>

            <PersonResult>
              <Person>
                <Name><Given>Teppo</Given><Family>Testinen</Family></Name>
                <Sex>M</Sex>
              </Person>
              <Organisation><Name>Test Club</Name></Organisation>

              <Result>
                <Time>2730</Time>
                <Status>OK</Status>
                <Position>1</Position>

                <ControlCard>1234567</ControlCard>

                <SplitTime>
                  <ControlCode>31</ControlCode>
                  <Time>600</Time>
                </SplitTime>
                <SplitTime>
                  <ControlCode>32</ControlCode>
                  <Time>1200</Time>
                </SplitTime>
                <SplitTime>
                  <ControlCode>33</ControlCode>
                  <Time>2000</Time>
                </SplitTime>
              </Result>
            </PersonResult>
          </ClassResult>
        </ResultList>
        """
    )

    xml_path = tmp_path / "results_minimal.xml"
    xml_path.write_text(xml_text, encoding="utf-8")

    # --- Act ----------------------------------------------------------
    # FI: Aja meidän tuontikomento. Lähdetiedot (source-name/url) vapaaehtoisia testissä.
    # EN: Run the import command. Provenance args are optional here.
    call_command("import_iofxml", "--file", str(xml_path))

    # --- Assert -------------------------------------------------------
    assert UploadedFile.objects.count() == 1

    # Competition
    assert Competition.objects.count() == 1
    comp = Competition.objects.first()
    assert comp.name == "Test Event"
    # FI: Lähdeviitteen pitäisi täyttyä uuteen UploadedFile-riviin.
    # EN: Source file link should be set to the new UploadedFile row.
    assert comp.source_file_id is not None

    # Course
    assert Course.objects.count() == 1
    course = Course.objects.first()
    # FI: 5000 m -> 5.0 km (ks. _length_to_km).
    # EN: 5000 m -> 5.0 km (see _length_to_km).
    assert course.length_km == 5.0

    # Athlete
    assert Athlete.objects.count() == 1
    ath = Athlete.objects.first()
    assert ath.first_name == "Teppo"
    assert ath.last_name == "Testinen"

    # Result
    assert Result.objects.count() == 1
    res = Result.objects.select_related("control_card").first()
    assert res.finish_time_s == 2730
    assert res.status == "OK"
    assert res.position == 1

    # Control card
    assert ControlCard.objects.count() == 1
    card = ControlCard.objects.first()
    assert card.uid == "1234567"
    # FI: Importer asettaa vendoriksi UNKNOWN ellei tunnisteta.
    # EN: Importer defaults vendor to UNKNOWN if not recognized.
    assert card.vendor == "UNKNOWN"
    assert res.control_card_id == card.id

    # Splits
    assert Split.objects.count() == 3
    codes = list(Split.objects.order_by("seq").values_list("control_code", flat=True))
    assert codes == ["31", "32", "33"]
