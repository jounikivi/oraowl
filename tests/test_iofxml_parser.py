# tests/test_iofxml_parser.py
# ============================================================
# FI: Testit IOF Data Standard 3.0 ResultList -parserille.
# EN: Tests for IOF Data Standard 3.0 ResultList parser.
# ============================================================

from __future__ import annotations

import os
from pathlib import Path
import unittest

from oraw_app.utils.iofxml_parser import parse_iofxml_result_list


# FI: Apu: polku tests/data -kansioon.
# EN: Helper: path to tests/data folder.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class IOFXMLParserMinimalTests(unittest.TestCase):
    """
    FI: Testit pienelle, yksinkertaiselle ResultList-esimerkkitiedostolle.
    EN: Tests for a small, minimal ResultList example file.
    """

    def test_parse_minimal_result_list_basic_fields(self) -> None:
        """
        FI: Varmistetaan, että perustiedot parsitaan oikein.
        EN: Ensure that basic fields are parsed correctly.
        """
        xml_path = DATA_DIR / "results_minimal.xml"
        with xml_path.open("rb") as f:
            xml_bytes = f.read()

        comp = parse_iofxml_result_list(xml_bytes)

        # Competition
        self.assertEqual(comp.name, "Test Event")
        self.assertEqual(comp.date, "2025-01-01")
        self.assertEqual(comp.organizer, "Test Club")

        # Classes / courses
        self.assertEqual(len(comp.classes), 1)
        class_res = comp.classes[0]
        self.assertEqual(class_res.class_name, "Men 21")
        self.assertEqual(class_res.course.name, "H21")
        self.assertEqual(class_res.course.length_m, 5000)

        # Results
        self.assertEqual(len(class_res.results), 1)
        res = class_res.results[0]

        # Athlete
        self.assertEqual(res.athlete.given_name, "Teppo")
        self.assertEqual(res.athlete.family_name, "Testinen")
        self.assertEqual(res.athlete.full_name, "Teppo Testinen")
        self.assertEqual(res.athlete.club_name, "Test Club")
        self.assertEqual(res.athlete.birth_date, "2000")
        self.assertEqual(res.athlete.iof_person_id, "1")

        # Result core
        self.assertEqual(res.status, "OK")
        self.assertEqual(res.time_seconds, 2730)
        self.assertEqual(res.position, 1)

        # Control card
        self.assertEqual(res.control_card, "1234567")
        self.assertEqual(res.punching_system, "SI")

        # Splits
        self.assertEqual(len(res.split_times), 3)
        codes = [st.control_code for st in res.split_times]
        times = [st.time_seconds for st in res.split_times]

        self.assertEqual(codes, ["31", "32", "33"])
        self.assertEqual(times, [600, 1200, 2000])


class IOFXMLParserSampleFileTests(unittest.TestCase):
    """
    FI: Testit isommalle ORAOWL_ResultList_sample.xml -tiedostolle.
    EN: Tests for the larger ORAOWL_ResultList_sample.xml file.
    """

    def test_parse_sample_result_list_structure(self) -> None:
        """
        FI: Varmistetaan, että rakenne ja määrät parsitaan oikein.
        EN: Ensure that structure and counts are parsed correctly.
        """
        xml_path = DATA_DIR / "ORAOWL_ResultList_sample.xml"
        with xml_path.open("rb") as f:
            xml_bytes = f.read()

        comp = parse_iofxml_result_list(xml_bytes)

        # Competition basic info
        self.assertEqual(comp.name, "Aura Sprintti 2025")
        self.assertEqual(comp.organizer, "Turun Suunnistajat")
        # Päivämäärä voi olla pelkkä '2025-08-15'
        self.assertEqual(comp.date, "2025-08-15")

        # We expect 2 class results: H21A and D16
        self.assertEqual(len(comp.classes), 2)
        class_names = sorted(c.class_name for c in comp.classes)
        self.assertEqual(class_names, ["D16", "H21A"])

        # H21A: 3 results, D16: 2 results (yht. 5)
        total_results = sum(len(c.results) for c in comp.classes)
        self.assertEqual(total_results, 5)

    def test_parse_sample_status_and_control_card(self) -> None:
        """
        FI: Tarkistetaan, että statukset ja leimauskortit näkyvät parserissa.
        EN: Check that statuses and control cards are present in parsed data.
        """
        xml_path = DATA_DIR / "ORAOWL_ResultList_sample.xml"
        with xml_path.open("rb") as f:
            xml_bytes = f.read()

        comp = parse_iofxml_result_list(xml_bytes)

        # Etsitään H21A-luokka
        h21a = next(c for c in comp.classes if c.class_name == "H21A")
        self.assertEqual(len(h21a.results), 3)

        # Järjestetään bib-numeroilla, jos saatavilla
        results_by_bib = sorted(
            h21a.results,
            key=lambda r: (r.bib_number or ""),
        )

        bibs = [r.bib_number for r in results_by_bib]
        # 101, 102, 103 ovat sample-tiedoston H21A-numerot
        self.assertEqual(bibs, ["101", "102", "103"])

        # Ensimmäinen (bib 101) on OK, ja hänellä on control_card
        first = results_by_bib[0]
        self.assertEqual(first.status, "OK")
        self.assertIsNotNone(first.control_card)
        self.assertTrue(first.control_card.startswith("SI-") or first.control_card.startswith("SI"))

        # Yksi tulos on Disqualified / DSQ-tyyppinen
        statuses = {r.status for r in h21a.results}
        self.assertIn("Disqualified", statuses)
