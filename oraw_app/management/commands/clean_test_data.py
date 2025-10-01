# oraw_app/management/commands/clean_test_data.py
from django.core.management.base import BaseCommand
from oraw_app.models import Competition, UploadedFile


class Command(BaseCommand):
    help = "Remove test data (e.g. 'Unnamed event' competitions and related UploadedFiles)."

    def handle(self, *args, **options):
        # 1. Poista kaikki kilpailut nimellä "Unnamed event"
        unnamed = Competition.objects.filter(name="Unnamed event")
        count_comp = unnamed.count()
        if count_comp > 0:
            self.stdout.write(f"Deleting {count_comp} competitions named 'Unnamed event'...")
            unnamed.delete()
        else:
            self.stdout.write("No 'Unnamed event' competitions found.")

        # 2. Etsi orphan-UploadedFile (joilla ei ole yhtään kilpailua viittauksena)
        orphan_files = UploadedFile.objects.filter(competitions_primary__isnull=True)
        count_files = orphan_files.count()
        if count_files > 0:
            self.stdout.write(f"Deleting {count_files} orphan UploadedFile(s)...")
            orphan_files.delete()
        else:
            self.stdout.write("No orphan UploadedFiles found.")

        self.stdout.write(self.style.SUCCESS("Clean-up completed."))
