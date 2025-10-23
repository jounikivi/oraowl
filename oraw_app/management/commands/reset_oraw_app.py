from __future__ import annotations

from typing import List, Tuple

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction

# Importoi omat mallit – järjestys: ensin riippuvaiset, sitten "vanhemmat"
from oraw_app.models import (
    Split,
    Result,
    ControlCard,
    Course,
    Competition,
    AthleteIdentifier,
    PrivacyPreference,
    AuditLog,
    Athlete,
    UploadedFile,
)


class Command(BaseCommand):
    help = (
        "Tyhjentää oraw_app-sovelluksen domain-datan turvallisesti. "
        "Säilyttää admin-/auth-käyttäjät. Käytä varoen."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-really-mean-it",
            action="store_true",
            dest="yes_i_really_mean_it",
            help="Ohita interaktiivinen varmistuskysymys.",
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

        models_in_delete_order: List = [
            # Lapset -> vanhemmat
            Split,
            Result,
            AthleteIdentifier,
            ControlCard,
            PrivacyPreference,
            AuditLog,
            Course,
            Competition,
            Athlete,
            UploadedFile,
        ]

        # Lasketaan rivimäärät etukäteen raportointia varten.
        def counts() -> List[Tuple[str, int]]:
            return [(m.__name__, m.objects.count()) for m in models_in_delete_order]

        pre = counts()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: ei poisteta mitään."))
            for name, n in pre:
                self.stdout.write(f"- {name}: {n}")
            self.stdout.write(self.style.SUCCESS("Valmis (dry-run)."))
            return

        if not skip_confirm:
            self.stdout.write(self.style.WARNING("Tämä poistaa oraw_app-sovelluksen datan."))
            self.stdout.write("Admin/auth-käyttäjiin ei kosketa.")
            answer = input("Kirjoita 'DELETE' jatkaaksesi: ").strip()
            if answer != "DELETE":
                self.stdout.write(self.style.NOTICE("Peruutettu."))
                return

        # Varmista, ettei mikään FK estä poistoja: Competition.source_file -> UploadedFile
        # Jos malli on NOT NULL, nollaa ennen poistoa; oletuksena meillä on nullable.
        with transaction.atomic():
            # Jos Competition.source_file ei ole nullable jossain tilanteessa, nollataan linkit varmuuden vuoksi.
            try:
                if apps.is_installed("oraw_app"):
                    Competition.objects.exclude(source_file=None).update(source_file=None)
            except Exception:
                # Jos ei onnistu tai kenttää ei ole, jatketaan – delete cascade hoitaa useimmat tapaukset.
                pass

            # Varsinainen poisto järjestyksessä
            for model in models_in_delete_order:
                deleted, _ = model.objects.all().delete()
                self.stdout.write(f"Poistettu {model.__name__}: {deleted}")

        # SQLite-optimointi
        if connection.vendor == "sqlite":
            with connection.cursor() as cur:
                cur.execute("VACUUM")
            self.stdout.write("SQLite VACUUM suoritettu.")

        post = counts()

        self.stdout.write(self.style.SUCCESS("oraw_app data wiped.\nYhteenveto:"))
        for (name_before, n_before), (_, n_after) in zip(pre, post):
            self.stdout.write(f"- {name_before}: {n_before} -> {n_after}")
        self.stdout.write(self.style.SUCCESS("(admin/auth käyttäjät säilytetty)"))
