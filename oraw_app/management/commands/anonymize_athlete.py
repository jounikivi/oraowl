# oraw_app/management/commands/anonymize_athlete.py
from __future__ import annotations

import sys
import uuid
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import timezone

from oraw_app.models import (
    Athlete,
    AthleteIdentifier,
    PrivacyPreference,
    AuditLog,
)


def _gen_alias(a: Athlete) -> str:
    """
    FI: Luo julkisen aliaksen. Muoto: Athlete-xxxxxxxx.
    EN: Generate a stable-looking public alias.
    """
    return f"Athlete-{str(a.id)[:8]}"


def _anonymize(athletes: Iterable[Athlete], reason: str, dry_run: bool) -> int:
    """
    FI: Anonymisoi urheilijan: piilota nimi, poista tunnisteet, lokita.
    EN: Anonymize athlete: hide name, clear identifiers, log.
    """
    count = 0
    now = timezone.now()

    for ath in athletes:
        new_alias = ath.public_alias or _gen_alias(ath)
        msg = f"[{ath.id}] {ath.last_name} {ath.first_name} -> alias={new_alias}"

        if dry_run:
            print(f"DRY-RUN {msg}")
            count += 1
            continue

        # Athlete: hide publicly but keep record (no hard delete)
        ath.public_alias = new_alias
        ath.is_public = False
        ath.deleted_at = None
        ath.deletion_reason = None
        ath.save(
            update_fields=[
                "public_alias",
                "is_public",
                "deleted_at",
                "deletion_reason",
            ]
        )

        # Ensure PrivacyPreference exists and hide name
        pref, _ = PrivacyPreference.objects.get_or_create(athlete=ath)
        if pref.hide_until and pref.hide_until > now.date():
            pass  # keep any future hide_until as is
        pref.show_name = False
        pref.suppressed_at = now
        pref.save(update_fields=["show_name", "suppressed_at"])

        # Drop identifiers (Emit/SI etc.)
        AthleteIdentifier.objects.filter(athlete=ath).delete()

        # Audit log
        AuditLog.objects.create(
            athlete=ath,
            event="anonymize",
            reason=reason or "Data subject request / admin action",
            by="management:anonymize_athlete",
            data_category="identity",
            processing_basis="legitimate_interest",
        )

        print(f"OK      {msg}")
        count += 1

    return count


class Command(BaseCommand):
    """
    FI: Anonymisoi urheilijan tiedot.
        Käyttö:
          python manage.py anonymize_athlete --id <UUID> [--reason "..."] [--dry-run]
          python manage.py anonymize_athlete --name "Etunimi Sukunimi" [--dry-run]
    EN: Anonymize an athlete's data.
        Usage:
          python manage.py anonymize_athlete --id <UUID> [--reason "..."] [--dry-run]
          python manage.py anonymize_athlete --name "First Last" [--dry-run]
    """

    help = "Anonymize athlete(s) for GDPR compliance."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=str, help="Athlete UUID (exact match).")
        parser.add_argument(
            "--name",
            type=str,
            help="Full or partial name match (first/last).",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="Data subject request",
            help="Reason for audit log.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only print actions.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Do not ask for confirmation.",
        )

    def handle(self, *args, **opts):
        id_str: str | None = opts.get("id")
        name: str | None = opts.get("name")
        reason: str = opts["reason"]
        dry_run: bool = bool(opts["dry_run"])
        assume_yes: bool = bool(opts["yes"])

        if not id_str and not name:
            raise CommandError('Provide --id <UUID> or --name "First Last"')

        qs = Athlete.objects.all()

        if id_str:
            try:
                uid = uuid.UUID(id_str)
            except ValueError as e:
                raise CommandError(f"Invalid UUID: {id_str}") from e
            qs = qs.filter(id=uid)

        if name:
            # case-insensitive partial match on either name part
            qs = qs.filter(
                models.Q(first_name__icontains=name)
                | models.Q(last_name__icontains=name)
            )

        athletes = list(qs)
        if not athletes:
            raise CommandError("No athletes matched criteria.")

        self.stdout.write(
            f"Matched {len(athletes)} athlete(s). dry_run={dry_run}"
        )

        if not assume_yes and not dry_run:
            self.stdout.write("Proceed? Type 'yes' to continue: ", ending="")
            self.stdout.flush()
            confirm = sys.stdin.readline().strip().lower()
            if confirm != "yes":
                raise CommandError("Aborted by user.")

        changed = _anonymize(athletes, reason=reason, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS(f"Done. Changed={changed}"))
