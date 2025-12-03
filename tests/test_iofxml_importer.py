# tests/test_iofxml_importer.py
# ============================================================
# FI: Testit IOF ResultList -importerille.
# EN: Tests for IOF ResultList importer.
# ============================================================

from __future__ import annotations

from pathlib import Path

from django.test import TestCase

from oraw_app.utils.iofxml_importer import import_iofxml_result_list
from oraw_app.models import (
    Competition,
    Course,
    Athlete,
    Result,
    Split,
    ControlCard,
)

# FI: Apu: polku tests/data -kansioon.
# EN: Helper: path to tests/data folder.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class IOFXMLImporterMinimalTests(TestCase):
    """
    FI: Testit importerille pienellä results_minimal.xml -tiedostolla.
    EN: Importer tests with the small results_minimal.xml file.
    """

    def test_import_minimal_creates_expected_objects(self) -> None:
        """
        FI: Varmistetaan, että ensimmäinen importointi luo oikeat määrät
            Competition, Course, Athlete, Result, Split ja ControlCard -olioita.
        EN: Ensure that the first import creates the expected number of
            Competition, Course, Athlete, Result, Split and ControlCard objects.
        """
        xml_path = DATA_DIR / "results_minimal.xml"
        if not xml_path.exists():
            self.skipTest(f"Test data file not found: {xml_path}")

        xml_bytes = xml_path.read_bytes()

        # FI: TestCase tyhjentää kannan, mutta tarkistetaan silti.
        self.assertEqual(Competition.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Athlete.objects.count(), 0)
        self.assertEqual(Result.objects.count(), 0)
        self.assertEqual(Split.objects.count(), 0)
        self.assertEqual(ControlCard.objects.count(), 0)

        report = import_iofxml_result_list(
            xml_bytes,
            filename="results_minimal.xml",
            uploaded_by=None,
        )

        # FI: Tarkistetaan tietokannan kokonaismäärät.
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Result.objects.count(), 1)
        self.assertEqual(Split.objects.count(), 3)
        self.assertEqual(ControlCard.objects.count(), 1)

        # FI: Varmistetaan myös raportin luvut.
        self.assertEqual(report.competitions_created, 1)
        self.assertEqual(report.competitions_updated, 0)
        self.assertEqual(report.courses_created, 1)
        self.assertEqual(report.athletes_created, 1)
        self.assertEqual(report.results_created, 1)
        self.assertEqual(report.results_updated, 0)
        self.assertEqual(report.splits_created, 3)

    def test_import_minimal_is_idempotent(self) -> None:
        """
        FI: Varmistetaan, että saman tiedoston tuominen kahdesti ei luo
            duplikaatteja Competition/Course/Athlete/Result/Split/ControlCard -olioihin.
        EN: Ensure that importing the same file twice does not create duplicate
            Competition/Course/Athlete/Result/Split and ControlCard objects.
        """
        xml_path = DATA_DIR / "results_minimal.xml"
        if not xml_path.exists():
            self.skipTest(f"Test data file not found: {xml_path}")

        xml_bytes = xml_path.read_bytes()

        # First import
        first_report = import_iofxml_result_list(
            xml_bytes,
            filename="results_minimal.xml",
            uploaded_by=None,
        )

        # FI: Ensimmäinen import luo datan.
        self.assertEqual(first_report.competitions_created, 1)
        self.assertEqual(first_report.results_created, 1)

        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Result.objects.count(), 1)
        self.assertEqual(Split.objects.count(), 3)
        self.assertEqual(ControlCard.objects.count(), 1)

        # Second import of the same file
        second_report = import_iofxml_result_list(
            xml_bytes,
            filename="results_minimal.xml",
            uploaded_by=None,
        )

        # FI: Ei duplikaatteja toisella importilla.
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Result.objects.count(), 1)
        self.assertEqual(Split.objects.count(), 3)
        self.assertEqual(ControlCard.objects.count(), 1)

        self.assertEqual(second_report.competitions_created, 0)
        self.assertEqual(second_report.results_created, 0)
