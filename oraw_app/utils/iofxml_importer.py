# oraw_app/utils/iofxml_importer.py
# ---------------------------------------------------------------
# FI: IOFXML 3.0 ResultList -tiedoston tuonti tietokantaan.
# EN: Import IOFXML 3.0 ResultList into the database.
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction

from oraw_app.utils.iofxml_parser import (
    ParsedCompetition,
    ParsedClassResult,
    ParsedResult,
    ParsedSplitTime,
    parse_iofxml_result_list,
)

from oraw_app.models import (
    Athlete,
    Competition,
    Course,
    Result,
    Split,
    ControlCard,
)


# ---------------------------------------------------------------
# FI: Raportti IOFXML-tuonnin lopputuloksesta.
# EN: Import report for IOFXML import.
# ---------------------------------------------------------------


@dataclass
class ImportReport:
    """
    FI: Yhteenveto IOFXML-tuonnista.
    EN: Summary of an IOFXML import run.
    """

    competitions_created: int = 0
    competitions_updated: int = 0
    courses_created: int = 0
    athletes_created: int = 0
    results_created: int = 0
    results_updated: int = 0
    splits_created: int = 0
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


# ---------------------------------------------------------------
# FI: Apu­funktiot (status, leimausjärjestelmä, kilpailu, rata, urheilija).
# EN: Helper functions (status, punching system, competition, course, athlete).
# ---------------------------------------------------------------


def _map_status(raw: Optional[str]) -> str:
    """
    FI: Muuntaa IOFXML-statuksen Result.STATUS_* -arvoihin.
    EN: Map IOFXML status into Result.STATUS_* values.
    """
    if not raw:
        return Result.STATUS_OK

    value = raw.strip().upper()

    if value in {"OK", "FINISHED"}:
        return Result.STATUS_OK

    if value in {"DNF", "DIDNOTFINISH"}:
        return Result.STATUS_DNF

    if value in {
        "DISQ",
        "DISQUALIFIED",
        "MISPUNCH",
        "MISSINGPUNCH",
        "MP",
    }:
        return Result.STATUS_DSQ

    # IOF: DidNotStart, OverTime, NotCompeting, Inactive, SportWithdrawn, ...
    if value in {"DNS", "DIDNOTSTART"}:
        return Result.STATUS_DNF

    return Result.STATUS_OTHER


def _map_punching_system(raw: Optional[str]) -> str:
    """
    FI: Muuntaa IOFXML:n PunchingSystem-arvon ControlCard.vendor-arvoksi.
    EN: Map IOFXML PunchingSystem into ControlCard.vendor.
    """
    if not raw:
        return ControlCard.VENDOR_UNKNOWN

    value = raw.strip().upper()

    if "EMIT" in value:
        return ControlCard.VENDOR_EMIT
    if "SI" in value or "SPORTIDENT" in value:
        return ControlCard.VENDOR_SI

    return ControlCard.VENDOR_OTHER


def _year_from_birth_date(birth_date: Optional[str]) -> Optional[int]:
    """
    FI: Ottaa syntymävuoden merkkijonosta (esim. '2000' tai '2000-05-01').
    EN: Extract year from birth date string (e.g. '2000' or '2000-05-01').
    """
    if not birth_date:
        return None
    s = birth_date.strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None


def _get_or_create_competition(
    parsed: ParsedCompetition,
    report: ImportReport,
) -> Competition:
    """
    FI: Hakee tai luo kilpailun ParsedCompetition-tietojen perusteella.
    EN: Get or create Competition based on ParsedCompetition data.
    """
    competition, created = Competition.objects.get_or_create(
        name=parsed.name,
        date=parsed.date,
        defaults={
            "organizer": parsed.organizer,
            "location": parsed.location,
        },
    )

    if created:
        report.competitions_created += 1
    else:
        changed = False
        for field, value in {
            "organizer": parsed.organizer,
            "location": parsed.location,
        }.items():
            if value and getattr(competition, field, None) != value:
                setattr(competition, field, value)
                changed = True

        if changed:
            competition.save()
            report.competitions_updated += 1

    return competition


def _get_or_create_course(
    competition: Competition,
    class_result: ParsedClassResult,
    report: ImportReport,
) -> Course:
    """
    FI: Hakee tai luo radan/sarjan (Course) kilpailulle.
    EN: Get or create Course for the given competition.
    """
    c = class_result.course

    length_km: Optional[Decimal] = None
    if c.length_m is not None:
        # FI: Metrit -> kilometrit (2 desimaalia).
        # EN: Convert meters -> kilometers (2 decimals).
        length_km = (Decimal(c.length_m) / Decimal("1000")).quantize(
            Decimal("0.01")
        )

    course, created = Course.objects.get_or_create(
        competition=competition,
        name=c.name,
        defaults={
            "length_km": length_km,
            "climb_m": c.climb_m,
        },
    )

    if created:
        report.courses_created += 1
    else:
        changed = False
        updates: dict[str, object] = {}

        if length_km is not None and course.length_km != length_km:
            updates["length_km"] = length_km
            changed = True

        if c.climb_m is not None and course.climb_m != c.climb_m:
            updates["climb_m"] = c.climb_m
            changed = True

        if changed:
            for field, value in updates.items():
                setattr(course, field, value)
            course.save()

    return course


def _get_or_create_athlete(parsed: ParsedResult, report: ImportReport) -> Athlete:
    """
    FI: Hakee tai luo urheilijan yhdistämällä nimen, seuran ja syntymävuoden.
    EN: Get or create Athlete using name, club and birth year as key.
    """
    a = parsed.athlete
    year = _year_from_birth_date(a.birth_date)

    # Jos etu-/sukunimi puuttuu, yritetään pilkkoa full_name.
    if not a.given_name and not a.family_name and a.full_name:
        parts = a.full_name.split()
        if len(parts) >= 2:
            given_name = " ".join(parts[:-1])
            family_name = parts[-1]
        else:
            given_name = a.full_name
            family_name = ""
    else:
        given_name = a.given_name or ""
        family_name = a.family_name or ""

    athlete, created = Athlete.objects.get_or_create(
        first_name=given_name,
        last_name=family_name,
        club=a.club_name,
        year_of_birth=year,
    )

    if created:
        report.athletes_created += 1

    return athlete


def _get_or_create_control_card(parsed: ParsedResult) -> Optional[ControlCard]:
    """
    FI: Hakee tai luo leimauskortin (Emit/SI/...), jos tiedot saatavilla.
    EN: Get or create control card (Emit/SI/...) if data is available.
    """
    if not parsed.control_card:
        return None

    uid = parsed.control_card.strip()
    vendor = _map_punching_system(parsed.punching_system)

    card, _ = ControlCard.objects.get_or_create(
        vendor=vendor,
        uid=uid,
    )
    return card


def _create_or_update_result(
    competition: Competition,
    course: Course,
    parsed: ParsedResult,
    athlete: Athlete,
    control_card: Optional[ControlCard],
    report: ImportReport,
) -> Result:
    """
    FI: Luo tai päivittää tulosrivin (Result) yhdelle urheilijalle.
    EN: Create or update a Result row for one athlete.
    """
    status = _map_status(parsed.status)

    result, created = Result.objects.update_or_create(
        course=course,
        athlete=athlete,
        defaults={
            "control_card": control_card,
            "finish_time_s": parsed.time_seconds,
            "status": status,
            "position": parsed.position,
            # FI: pace_s_per_km lasketaan myöhemmin erillisessä prosessissa.
            # EN: pace_s_per_km is calculated later in a separate process.
        },
    )

    if created:
        report.results_created += 1
    else:
        report.results_updated += 1

    # FI: Poistetaan vanhat väliajat ja luodaan uudet.
    # EN: Delete old splits and create new ones.
    Split.objects.filter(result=result).delete()

    bulk_splits: list[Split] = []

    prev_cum: Optional[int] = None
    for split in parsed.split_times:
        bulk_splits.append(_build_split_model(result, split, prev_cum))
        # Päivitä edellinen kumulatiivinen, jos nykyinen ei ole None
        if split.time_seconds is not None:
            prev_cum = split.time_seconds

    if bulk_splits:
        Split.objects.bulk_create(bulk_splits)
        report.splits_created += len(bulk_splits)

    return result


def _build_split_model(
    result: Result,
    split: ParsedSplitTime,
    prev_cum: Optional[int],
) -> Split:
    """
    FI: Rakentaa Split-mallin ParsedSplitTime-tiedosta.
        IOFXML:n aika tulkitaan kumulatiiviseksi ajaksi (Time / time),
        josta lasketaan väliaika (split_time_s).
    EN: Build Split model from ParsedSplitTime.
        IOFXML time is interpreted as cumulative time from start
        (Time / time), from which leg split_time_s is derived.
    """
    cum = split.time_seconds
    if cum is None:
        split_time_s = 0
        cum_time_s = None
    else:
        if prev_cum is None:
            split_time_s = cum
        else:
            split_time_s = cum - prev_cum
            if split_time_s < 0:
                # Varmuuden vuoksi, jos data on epäloogista.
                split_time_s = cum
        cum_time_s = cum

    return Split(
        result=result,
        seq=split.sequence,
        control_code=split.control_code or "",
        split_time_s=split_time_s,
        cum_time_s=cum_time_s,
    )


# ---------------------------------------------------------------
# FI: Julkinen rajapinta IOFXML-tiedoston tuontiin.
# EN: Public API for importing an IOFXML file.
# ---------------------------------------------------------------


def import_iofxml_result_list(
    xml_bytes: bytes,
    *,
    filename: Optional[str] = None,
    uploaded_by: Optional[object] = None,
) -> ImportReport:
    """
    FI:
        Korkean tason IOFXML-tuonti. Parsii XML:n, luo tarvittaessa
        kilpailun, radat, urheilijat, tulokset ja väliajat, ja
        palauttaa ImportReport-yhteenvedon.

        Huomio:
        - filename ja uploaded_by ovat varattu tulevaa käyttöä varten,
          mutta niitä ei tässä vaiheessa vielä käytetä.

    EN:
        High-level IOFXML import. Parses the XML, creates or updates
        competitions, courses, athletes, results and split times, and
        returns an ImportReport summary.

        Note:
        - filename and uploaded_by are reserved for future use but are
          not used at this stage.
    """
    report = ImportReport()

    # 1) Parse IOFXML into an in-memory structure.
    parsed_competition: ParsedCompetition = parse_iofxml_result_list(xml_bytes)

    # 2) Wrap DB operations in a single transaction.
    with transaction.atomic():
        competition = _get_or_create_competition(parsed_competition, report)

        for class_result in parsed_competition.classes:
            course = _get_or_create_course(competition, class_result, report)

            for parsed_result in class_result.results:
                athlete = _get_or_create_athlete(parsed_result, report)
                control_card = _get_or_create_control_card(parsed_result)
                _create_or_update_result(
                    competition=competition,
                    course=course,
                    parsed=parsed_result,
                    athlete=athlete,
                    control_card=control_card,
                    report=report,
                )

    return report
