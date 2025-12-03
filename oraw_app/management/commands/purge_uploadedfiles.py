from __future__ import annotations
import os
from datetime import date
from django.core.management.base import BaseCommand
#from django.utils.timezone import now
from django.db import transaction

from oraw_app.models.uploaded_file import UploadedFile


class Command(BaseCommand):
    """
    FI: Poistaa ne UploadedFile-rivit, joiden retention_until on mennyt.
        Poistaa sekä tietokantarivin että fyysisen IOFXML-tiedoston.

    EN: Purges UploadedFile rows whose retention_until is in the past.
        Deletes both the database row and the physical file.
    """

    help = (
        "Purge UploadedFile entries whose retention_until date is in the past. "
        "Deletes both database rows and the actual XML files. "
        "Supports --dry-run and --yes flags."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not delete anything. Only show what would be removed.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_confirm = options["yes"]

        today = date.today()

        # Fetch all files eligible for deletion
        qs = UploadedFile.objects.filter(
            retention_until__isnull=False,
            retention_until__lt=today,
        )

        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Ei poistettavia tiedostoja."))
            return

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Poistettavat tiedostot:"))
        for f in qs:
            self.stdout.write(
                f" - {f.original_name} "
                f"(uploaded: {f.uploaded_at.date()}, "
                f"retention_until: {f.retention_until}, "
                f"sha256: {f.sha256[:12]}...)"
            )

        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY-RUN: {total} tiedostoa olisi poistettu, mutta mitään ei tehty."
                )
            )
            return

        if not skip_confirm:
            confirm = input(
                f"Olet poistamassa {total} tiedostoa. "
                f"Tämä poistaa myös fyysiset XML-tiedostot.\n"
                "Vahvista kirjoittamalla 'yes': "
            )
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.ERROR("Peruutettu."))
                return

        deleted_files = 0

        with transaction.atomic():
            for f in qs:
                file_path = f.stored_file.path

                # Delete DB row
                f.delete()
                deleted_files += 1

                # Delete physical file (if exists)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"[VAROITUS] Tietokantarivi poistettu, mutta tiedoston "
                                f"poistossa virhe: {file_path} ({e})"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[HUOM] Fyysinen tiedosto puuttui jo: {file_path}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Poistettu {deleted_files} UploadedFile-riviä ja niiden fyysiset XML-tiedostot."
            )
        )
