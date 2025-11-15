# oraw_app/utils/iofxml_importer.py
# ---------------------------------------------------------------
# FI: IOFXML 3.0 ResultList -tiedoston tuonti tietokantaan.
# EN: Import IOFXML 3.0 ResultList into the database.
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from django.db import transaction

from oraw_app.utils.iofxml_parser import (
    ParsedCompetition,
    ParsedClassResult,
    ParsedResult,
    parse_iofxml_result_list,
)

if TYPE_CHECKING:
    # FI: Käytetään Django User -mallia vain tyypityksessä.
    # EN: Use Django's User model for type checking only.
    from django.contrib.auth.models import AbstractUser as User


# HUOM / NOTE:
# FI: Säädä nämä importit vastaamaan omia mallejasi, jos nimet eroavat.
# EN: Adjust these imports to match your actual models if names differ.
from oraw_app.models import (
    Competition,
    Course,
    Athlete,       # vai Runner tms. → muuta tarvittaessa
    Result,
    Split,
    ControlCard,
    UploadedFile,
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
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


# ---------------------------------------------------------------
# FI: Sisäiset apufunktiot (korttijärjestelmä, haku/lisäys).
# EN: Internal helpers (punching system, lookup/create).
# ---------------------------------------------------------------

def _map_punching_system(raw: Optional[str]) -> str:
    """
    FI: Muuntaa IOFXML:n PunchingSystem-arvon vendor-tyyppiin.
    EN: Map IOFXML PunchingSystem into a normalized vendor string.
    """
    if not raw:
        return "UNKNOWN"
    value = raw.strip().upper()
    if "EMIT" in value:
        return "EMIT"
    if "SI" in value or "SPORTIDENT" in value:
        return "SI"
    return value  # esim. muu tunniste


def _get_or_create_competition(
    parsed: ParsedCompetition,
    uploaded_file: Optional[UploadedFile],
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
            "iof_event_id": parsed.iof_event_id,
            "source_file": uploaded_file,
        },
    )

    if created:
        report.competitions_created += 1
    else:
        # Päivitä perustiedot varovasti
        changed = False
        for field, value in {
            "organizer": parsed.organizer,
            "location": parsed.location,
            "iof_event_id": parsed.iof_event_id,
        }.items():
            if value and getattr(competition, field, None) != value:
                setattr(competition, field, value)
                changed = True
        if uploaded_file is not None and getattr(competition, "source_file", None) is None:
            competition.source_file = uploaded_file
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
    course_data = class_result.course

    course, created = Course.objects.get_or_create(
        competition=competition,
        name=course_data.name,
        defaults={
            "length_m": course_data.length_m,
            "climb_m": course_data.climb_m,
            "controls_count": course_data.controls_count,
        },
    )

    if created:
        report.courses_created += 1
    else:
        changed = False
        for field, value in {
            "length_m": course_data.length_m,
            "climb_m": course_data.climb_m,
            "controls_count": course_data.controls_count,
        }.items():
            if value is not None and getattr(course, field, None) != value:
                setattr(course, field, value)
                changed = True
        if changed:
            course.save()

    return course


def _get_or_create_athlete(parsed: ParsedResult, report: ImportReport) -> Athlete:
    """
    FI: Hakee tai luo urheilijan yhdistämällä nimen, seuran ja syntymäajan.
    EN: Get or create Athlete using name, club and birth date as key.
    """
    a = parsed.athlete

    # Matchataan nimen + seuran + syntymäajan perusteella.
    athlete, created = Athlete.objects.get_or_create(
        full_name=a.full_name,
        club_name=a.club_name,
        birth_date=a.birth_date,
        defaults={
            "given_name": a.given_name,
            "family_name": a.family_name,
            "gender": a.gender,
            "iof_person_id": a.iof_person_id,
        },
    )

    if created:
        report.athletes_created += 1
    else:
        # Päivitetään olemassa olevan rivin lisätietoja, jos puuttuu.
        changed = False
        for field, value in {
            "given_name": a.given_name,
            "family_name": a.family_name,
            "gender": a.gender,
            "iof_person_id": a.iof_person_id,
        }.items():
            if value and not getattr(athlete, field, None):
                setattr(athlete, field, value)
                changed = True
        if changed:
            athlete.save()

    return athlete


def _get_or_create_control_card(parsed: ParsedResult) -> Optional[ControlCard]:
    """
    FI: Hakee tai luo leimauskortin (Emit/SI) jos tiedot ovat saatavilla.
    EN: Get or create control card (Emit/SI) if data is available.
    """
    if not parsed.control_card:
        return None

    vendor = _map_punching_system(parsed.punching_system)
    uid = parsed.control_card.strip()

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
    result, created = Result.objects.update_or_create(
        course=course,
        athlete=athlete,
        defaults={
            "competition": competition,
            "club_name": athlete.club_name,
            "bib_number": parsed.bib_number,
            "status": parsed.status,
            "time_seconds": parsed.time_seconds,
            "position": parsed.position,
            "control_card": control_card,
        },
    )

    if created:
        report.results_created += 1
    else:
        report.results_updated += 1

    # Poistetaan vanhat väliajat ja luodaan uudet.
    Split.objects.filter(result=result).delete()

    bulk_splits: list[Split] = []
    for split in parsed.split_times:
        bulk_splits.append(
            Split(
                result=result,
                sequence=split.sequence,
                control_code=split.control_code,
                time_seconds=split.time_seconds,
                status=split.status,
                position=split.position,
            )
        )

    if bulk_splits:
        Split.objects.bulk_create(bulk_splits)
        report.splits_created += len(bulk_splits)

    return result


# ---------------------------------------------------------------
# FI: Julkinen rajapinta IOFXML-tiedoston tuontiin.
# EN: Public API for importing an IOFXML file.
# ---------------------------------------------------------------

def import_iofxml_result_list(
    xml_bytes: bytes,
    *,
    filename: Optional[str] = None,
    uploaded_by: Optional["User"] = None,
) -> ImportReport:
    """
    FI:
        Korkean tason IOFXML-tuonti. Parsii XML:n, luo tarvittaessa
        kilpailun, radat, urheilijat, tulokset ja väliajat, ja
        palauttaa ImportReport-yhteenvedon.

        Huomio:
        - Tiedosto voidaan tallentaa UploadedFile-malliin, jos halutaan
          säilyttää alkuperäinen IOFXML talteen.

    EN:
        High-level IOFXML import. Parses the XML, creates or updates
        competitions, courses, athletes, results and split times, and
        returns an ImportReport summary.

        Note:
        - The original IOFXML can be stored in UploadedFile if you
          want to keep the source file.
    """
    report = ImportReport()

    # 1) Parsitaan XML väliaikaiseen rakenteeseen.
    parsed_competition: ParsedCompetition = parse_iofxml_result_list(xml_bytes)

    # 2) Tallennetaan haluttaessa UploadedFile (vain metatietona tässä).
    uploaded_file: Optional[UploadedFile] = None
    if filename:
        uploaded_file = UploadedFile.objects.create(
            original_name=filename,
            # FI: Varsinainen tiedosto voidaan tallentaa erikseen
            # EN: The actual file content can be attached separately
            uploaded_by=uploaded_by,
            source_type="iofxml_result_list",
        )

    # 3) Kaikki tietokantaoperaatiot samassa transaktiossa.
    with transaction.atomic():
        competition = _get_or_create_competition(parsed_competition, uploaded_file, report)

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
