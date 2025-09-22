# oraw_app/management/commands/import_iofxml.py
from __future__ import annotations

from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from oraw_app.models import UploadedFile
from oraw_app.utils.iofxml import sha256_of_file
from oraw_app.utils.iofxml_importer import import_result_list


class Command(BaseCommand):
    help = "Import IOF v3 ResultList XML: store original file and parse it."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to IOF XML (ResultList).")
        parser.add_argument("--source-name", help="Provenance label (optional).")
        parser.add_argument("--source-url", help="Provenance URL (optional).")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        digest = sha256_of_file(path)
        existing = UploadedFile.objects.filter(sha256=digest).first()

        if existing:
            self.stdout.write(self.style.WARNING("File already uploaded (sha256 match)."))
            xml_bytes = existing.stored_file.read() if existing.stored_file else path.read_bytes()
            comp, n_ath, n_res = import_result_list(xml_bytes, source_file=existing)
            return self._report(existing, comp, n_ath, n_res, reused=True)

        # Store original file
        xml_bytes = path.read_bytes()
        up = UploadedFile(
            original_name=path.name,
            size_bytes=path.stat().st_size,
            sha256=digest,
            source_name=opts.get("source_name") or None,
            source_url=opts.get("source_url") or None,
        )
        up.stored_file.save(path.name, ContentFile(xml_bytes), save=True)

        comp, n_ath, n_res = import_result_list(xml_bytes, source_file=up)
        return self._report(up, comp, n_ath, n_res, reused=False)

    def _report(self, up: UploadedFile, comp, n_ath: int, n_res: int, reused: bool):
        flag = "REUSED" if reused else "STORED"
        self.stdout.write(self.style.SUCCESS(f"Import completed [{flag}]."))
        self.stdout.write(f"UploadedFile: {up.original_name} ({up.sha256[:8]}...)")
        self.stdout.write(f"Competition:  {comp}")
        self.stdout.write(f"Athletes new: {n_ath}")
        self.stdout.write(f"Results new:  {n_res}")
