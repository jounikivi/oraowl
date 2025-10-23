from __future__ import annotations

from typing import List, Tuple

from django.core.management.base import BaseCommand
from django.db import connection, transaction


# Taulujen nimet suoraan – vältetään ORM:ää ja kenttämuunnoksia kokonaan.
TABLES_IN_DELETE_ORDER = [
    "oraw_app_split",
    "oraw_app_result",
    "oraw_app_athleteidentifier",
    "oraw_app_controlcard",
    "oraw_app_privacypreference",
    "oraw_app_auditlog",
    "oraw_app_course",
    "oraw_app_competition",
    "oraw_app_athlete",
    "oraw_app_uploadedfile",
]

# Erilliset toimet FK-riippuvuuksien takia
# Competition.source_file_id viittaa UploadedFileen -> NULL ennen UploadedFile-poistoa
FK_NULLING_SQL = [
    "UPDATE oraw_app_competition SET source_file_id = NULL WHERE source_file_id IS NOT NULL",
]


def _count_rows() -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    with connection.cursor() as cur:
        for t in TABLES_IN_DELETE_ORDER:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            n = cur.fetchone()[0]
            out.append((t, n))
    return out


class Command(BaseCommand):
    help = (
        "Tyhjentää oraw_app-sovelluksen domain-datan raakana (SQL). "
        "Säilyttää auth/admin-käyttäjät. Käytä varoen."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-really-mean-it",
            action="store_true",
            dest="yes_i_really_mean_it",
            help="Ohita interaktiivinen varmistus.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Näytä mitä poistettaisiin, mutta älä poista mitään.",
        )

    def handle(self, *args, **options):
        skip_confirm: bool = options["yes_i_really_mean_it"]
        dry_run: bool = options["dry_run"]

        before = _count_rows()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: ei poisteta mitään."))
            for t, n in before:
                self.stdout.write(f"- {t}: {n}")
            self.stdout.write(self.style.SUCCESS("Valmis (dry-run)."))
            return

        if not skip_confirm:
            self.stdout.write(self.style.WARNING("Tämä poistaa oraw_app-datan raakana SQL:llä."))
            self.stdout.write("Admin/auth-käyttäjiin ei kosketa.")
            ans = input("Kirjoita 'DELETE' jatkaaksesi: ").strip()
            if ans != "DELETE":
                self.stdout.write(self.style.NOTICE("Peruutettu."))
                return

        with transaction.atomic():
            with connection.cursor() as cur:
                # Varmuuden vuoksi pidetään SQLite FK:t päällä
                if connection.vendor == "sqlite":
                    cur.execute("PRAGMA foreign_keys = ON")

                # Nollaa FK:t, jotka estäisivät poiston
                for sql in FK_NULLING_SQL:
                    cur.execute(sql)

                # Poistot lapsista vanhempiin
                for t in TABLES_IN_DELETE_ORDER:
                    # Tulosta poistomäärä selkeästi
                    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
                    n = cur.fetchone()[0]
                    cur.execute(f'DELETE FROM "{t}"')
                    self.stdout.write(f"Poistettu {t}: {n}")

        # Siivoa SQLite
        if connection.vendor == "sqlite":
            with connection.cursor() as cur:
                cur.execute("VACUUM")
            self.stdout.write("SQLite VACUUM suoritettu.")

        after = _count_rows()
        self.stdout.write(self.style.SUCCESS("oraw_app data wiped.\nYhteenveto:"))
        for (t_before, n_before), (_, n_after) in zip(before, after):
            self.stdout.write(f"- {t_before}: {n_before} -> {n_after}")
        self.stdout.write(self.style.SUCCESS("(admin/auth käyttäjät säilytetty)"))
