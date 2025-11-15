# oraw_app/management/commands/import_iofxml.py
# ---------------------------------------------------------------
# FI: Komento IOFXML 3.0 ResultList -tiedoston tuontiin.
# EN: Management command for importing an IOFXML 3.0 ResultList file.
# ---------------------------------------------------------------

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from oraw_app.utils.iofxml_importer import import_iofxml_result_list


class Command(BaseCommand):
    """
    FI:
        Tuontikomento IOFXML ResultList -tiedostoille. Käyttää
        oraw_app.utils.iofxml_importer.import_iofxml_result_list
        -funktiota ja tulostaa yhteenvedon tuonnista.

    EN:
        Import command for IOFXML ResultList files. Uses
        oraw_app.utils.iofxml_importer.import_iofxml_result_list
        and prints an import summary.
    """

    help = (
        "FI: Tuo IOFXML 3.0 ResultList -tiedoston tietokantaan.\n"
        "EN: Import an IOFXML 3.0 ResultList file into the database."
    )

    def add_arguments(self, parser) -> None:
        """
        FI:
            path: Polku IOFXML-tiedostoon (esim. tests/data/results_minimal.xml).

        EN:
            path: Path to the IOFXML file
                  (e.g. tests/data/results_minimal.xml).
        """
        parser.add_argument(
            "path",
            type=str,
            help=(
                "FI: Polku IOFXML ResultList -tiedostoon. "
                "EN: Path to IOFXML ResultList file."
            ),
        )

    def handle(self, *args, **options) -> None:
        path = options["path"]

        if not os.path.exists(path):
            raise CommandError(
                f"FI: Tiedostoa ei löydy: {path}\n"
                f"EN: File does not exist: {path}",
            )

        try:
            with open(path, "rb") as f:
                xml_bytes = f.read()
        except OSError as exc:
            raise CommandError(
                f"FI: Tiedoston lukeminen epäonnistui: {exc}\n"
                f"EN: Failed to read file: {exc}",
            ) from exc

        filename = os.path.basename(path)

        # FI: Suoritetaan varsinainen tuonti.
        # EN: Run the actual import.
        report = import_iofxml_result_list(
            xml_bytes,
            filename=filename,
            uploaded_by=None,
        )

        # FI: Tulostetaan yhteenveto.
        # EN: Print summary.
        self.stdout.write(self.style.SUCCESS("IOFXML import completed."))
        self.stdout.write(
            f"FI: Kilpailuja luotu: {report.competitions_created}, "
            f"päivitetty: {report.competitions_updated}",
        )
        self.stdout.write(
            f"EN: Competitions created: {report.competitions_created}, "
            f"updated: {report.competitions_updated}",
        )
        self.stdout.write(
            f"FI: Ratoja luotu: {report.courses_created}\n"
            f"EN: Courses created: {report.courses_created}",
        )
        self.stdout.write(
            f"FI: Urheilijoita luotu: {report.athletes_created}\n"
            f"EN: Athletes created: {report.athletes_created}",
        )
        self.stdout.write(
            f"FI: Tuloksia luotu: {report.results_created}, "
            f"päivitetty: {report.results_updated}",
        )
        self.stdout.write(
            f"EN: Results created: {report.results_created}, "
            f"updated: {report.results_updated}",
        )
        self.stdout.write(
            f"FI: Väliaikoja luotu: {report.splits_created}\n"
            f"EN: Splits created: {report.splits_created}",
        )

        if report.warnings:
            self.stdout.write("")
            self.stdout.write("FI: Huomiot / varoitukset:")
            self.stdout.write("EN: Warnings / notes:")
            for msg in report.warnings:
                self.stdout.write(f"- {msg}")
