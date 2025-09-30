# oraw_app/management/commands/purge_uploadedfiles.py
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from oraw_app.models import UploadedFile


class Command(BaseCommand):
    """
    FI: Poista UploadedFile-rivit, joiden retention_until on menneisyydessä.
    EN: Delete UploadedFiles whose retention_until is in the past.
    """
    help = "Delete UploadedFiles past retention date (retention_until < today)."

    def handle(self, *args, **options):
        today = now().date()
        qs = UploadedFile.objects.filter(
            retention_until__isnull=False,
            retention_until__lt=today,
        )
        count = qs.count()
        if count == 0:
            self.stdout.write("No files to purge.")
            return

        # FI: Poisto poistaa myös FileFieldin fyysisen tiedoston, jos storage on konffattu.
        # EN: Deleting model rows also deletes physical files if storage is configured.
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {count} UploadedFile(s)."))
