from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from oraw_app.utils.iofxml_importer import import_result_list


class Command(BaseCommand):
    help = "Import IOF XML ResultList into ORAOwl"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to IOF XML ResultList file (3.0/3.1).",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise CommandError(f"File not found: {file_path}")

        # Read bytes
        xml_bytes = p.read_bytes()

        # Call importer with new signature
        report = import_result_list(file_bytes=xml_bytes, filename=p.name)

        # Print a compact summary
        self.stdout.write(self.style.SUCCESS("Import finished."))
        self.stdout.write(
            f"  Competitions created: {report.competitions_created}\n"
            f"  Courses created:      {report.courses_created}\n"
            f"  Athletes created:     {report.athletes_created}\n"
            f"  Results created:      {report.results_created}\n"
            f"  Splits created:       {report.splits_created}\n"
            f"  Control cards:        {report.control_cards_created}\n"
            f"  UploadedFile:         {report.uploaded_file.id if report.uploaded_file else '-'}"
        )
