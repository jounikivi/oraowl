from __future__ import annotations

"""
FI: IOFXML ResultList -tuonti. Kestää "oikean kisadatan" vaihtelut:
    - Course.Length metreinä -> tallennetaan kilometreinä (Decimal, 3 desimaalia)
    - Climb metreinä (int)
    - Result/Time ja SplitTime -> sekunneiksi useista eri muodoista
    - Status normalisoidaan (OK, DNS, DNF, MP, DSQ)
    - Virheelliset/tyhjät arvot -> None (ei kaada tuontia)

EN: IOFXML ResultList importer. Robust against real-world data quirks:
    - Course.Length in meters -> store as kilometers (Decimal, 3 decimals)
    - Climb in meters (int)
    - Result/Time and SplitTime -> converted to seconds from multiple formats
    - Status normalized (OK, DNS, DNF, MP, DSQ)
    - Invalid/missing values -> None (won't crash the import)
"""

import hashlib
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from oraw_app.models import (
    Competition,
    Course,
    Athlete,
    Result,
    Split,
    ControlCard,
    UploadedFile,
)

from .normalizers import (
    parse_length_km_from_meters,
    parse_climb_m,
    parse_time_to_seconds,
    normalize_status,
)


# -----------------------------------------------------------------------------
# IOF XML namespace (3.0)
# -----------------------------------------------------------------------------
NS = {"iof": "http://www.orienteering.org/datastandard/3.0"}


@dataclass
class ImportReport:
    """
    FI: Yksinkertainen raportti, jota voidaan näyttää UI:ssa tuonnin jälkeen.
    EN: Simple report shown in UI after the import completes.
    """

    competitions_created: int = 0
    courses_created: int = 0
    athletes_created: int = 0
    results_created: int = 0
    splits_created: int = 0
    files_deduplicated: bool = False
    message: str = "OK"


def _text(el: Optional[ET.Element]) -> Optional[str]:
    """
    FI: Palauttaa elementin tekstin tai None.
    EN: Returns element text or None.
    """
    if el is None:
        return None
    t = (el.text or "").strip()
    return t or None


def _sha256_bytes(data: bytes) -> str:
    """
    FI: Sha256 tarkiste (UploadedFile-deduplikointiin).
    EN: Sha256 digest for UploadedFile deduplication.
    """
    return hashlib.sha256(data).hexdigest()


def _ensure_uploaded_file(xml_bytes: bytes, uploaded_by=None) -> UploadedFile:
    """
    FI: Tallentaa lähde-XML:n UploadedFile-tauluun sha256-deduplikoiden.
    EN: Saves the source XML into UploadedFile with sha256 de-duplication.
    """
    digest = _sha256_bytes(xml_bytes)
    uf, created = UploadedFile.objects.get_or_create(
        sha256=digest,
        defaults={"content": xml_bytes, "uploaded_by": uploaded_by},
    )
    return uf


def _parse_competition(root: ET.Element) -> dict:
    """
    FI: Poimii kilpailun perustiedot: nimi, päivämäärä, järjestäjä, paikka.
    EN: Extract event basics: name, date, organiser, venue.
    """
    event = root.find("iof:Event", NS)
    name = _text(event.find("iof:Name", NS)) if event is not None else None
    venue = _text(event.find("iof:Venue", NS)) if event is not None else None

    # Date (use first StartTime/Date if present)
    date_el = root.find("iof:Event/iof:StartTime/iof:Date", NS)
    date_str = _text(date_el)
    date = None
    if date_str:
        try:
            # YYYY-MM-DD expected by IOF; naive date is OK for a competition date
            from datetime import date as d

            parts = [int(p) for p in date_str.split("-")]
            date = d(parts[0], parts[1], parts[2])
        except Exception:
            date = None

    # Organiser
    org_el = root.find(
        "iof:Event/iof:Organiser/iof:Organisation/iof:Name", NS
    )
    organiser = _text(org_el)

    return {
        "name": name or "Unnamed Event",
        "date": date,
        "organizer": organiser,
        "location": venue,
    }


def _get_or_create_athlete(class_result: ET.Element) -> tuple[Athlete, bool]:
    """
    FI: Luo/hakee Athlete-olion PersonResultista. Käytetään nimeä + seuraa.
    EN: Creates/gets Athlete from PersonResult. Uses name + club.
    """
    person = class_result.find("iof:PersonResult/iof:Person", NS)
    given = _text(person.find("iof:Name/iof:Given", NS)) if person is not None else None
    family = _text(person.find("iof:Name/iof:Family", NS)) if person is not None else None
    full_name = " ".join([p for p in [given, family] if p]).strip() or "Unknown"

    org = class_result.find(
        "iof:PersonResult/iof:Organisation/iof:Name", NS
    )
    club = _text(org)

    athlete, created = Athlete.objects.get_or_create(
        name=full_name,
        defaults={"club": club},
    )
    # Update club if missing
    if not athlete.club and club:
        athlete.club = club
        athlete.save(update_fields=["club"])
    return athlete, created


def _get_or_create_course_for_class(class_result: ET.Element, comp: Competition) -> tuple[Course, bool]:
    """
    FI: Luo/hakee Course-olion ClassResultin Course-tiedoista.
    EN: Creates/gets Course from ClassResult's Course info.
    """
    course_el = class_result.find("iof:Course", NS)
    course_name = _text(course_el.find("iof:Name", NS)) if course_el is not None else None
    length_m = _text(course_el.find("iof:Length", NS)) if course_el is not None else None
    climb_m = _text(course_el.find("iof:Climb", NS)) if course_el is not None else None

    course_name = course_name or _text(class_result.find("iof:Class/iof:Name", NS)) or "Unnamed"

    length_km = parse_length_km_from_meters(length_m)
    climb = parse_climb_m(climb_m)

    course, created = Course.objects.get_or_create(
        competition=comp,
        name=course_name,
        defaults={
            "length_km": length_km,
            "climb_m": climb,
        },
    )
    # Update length/climb if missing previously
    fields_to_update = []
    if course.length_km is None and length_km is not None:
        course.length_km = length_km
        fields_to_update.append("length_km")
    if getattr(course, "climb_m", None) is None and climb is not None:
        # model may be optional; only update if field exists
        try:
            getattr(course, "climb_m")
            course.climb_m = climb
            fields_to_update.append("climb_m")
        except AttributeError:
            pass
    if fields_to_update:
        course.save(update_fields=fields_to_update)
    return course, created


def _create_result_and_splits(class_result: ET.Element, course: Course, athlete: Athlete) -> tuple[Optional[Result], int]:
    """
    FI: Luo Result + Splitit yhdestä ClassResultista. Palauttaa Resultin ja
        luotujen Split-rivien määrän.
    EN: Creates Result + Splits for one ClassResult. Returns Result and the
        number of created Split rows.
    """
    person_result = class_result.find("iof:PersonResult", NS)
    if person_result is None:
        return None, 0

    res_el = person_result.find("iof:Result", NS)
    time_val = _text(res_el.find("iof:Time", NS)) if res_el is not None else None
    status_val = _text(res_el.find("iof:Status", NS)) if res_el is not None else None
    control_card_val = _text(res_el.find("iof:ControlCard", NS)) if res_el is not None else None
    position_val = _text(res_el.find("iof:Position", NS)) if res_el is not None else None

    time_s = parse_time_to_seconds(time_val)
    status = normalize_status(status_val)

    # ControlCard (optional)
    cc = None
    if control_card_val:
        cc, _ = ControlCard.objects.get_or_create(
            vendor="UNKNOWN",  # FI: Ei aina tiedossa; päivitä jos vendor havaitaan
            uid=control_card_val,
        )

    result = Result.objects.create(
        athlete=athlete,
        course=course,
        total_time_s=time_s,
        status=status,
        position=parse_int(position_val) if position_val else None,
        control_card=cc,
    )

    # Splits
    splits_created = 0
    for st in person_result.findall("iof:Result/iof:SplitTime", NS):
        code = _text(st.find("iof:ControlCode", NS))
        split_time_val = _text(st.find("iof:Time", NS))
        cum_time_val = _text(st.find("iof:CumulativeTime", NS))

        split_s = parse_time_to_seconds(split_time_val)
        cum_s = parse_time_to_seconds(cum_time_val)

        # Sequence number: attempt from order in list
        seq = splits_created + 1

        Split.objects.create(
            result=result,
            sequence=seq,
            control_code=code or "",
            split_time_s=split_s,
            cum_time_s=cum_s,
        )
        splits_created += 1

    return result, splits_created


@transaction.atomic
def import_result_list(
    file_obj_or_path: io.BufferedIOBase | str,
    uploaded_by=None,
) -> ImportReport:
    """
    FI: Tuo IOFXML ResultList -tiedoston tietokantaan.
        Palauttaa raportin (montako riviä luotiin jne.).
    EN: Imports an IOFXML ResultList file into the database.
        Returns a report of created rows etc.
    """
    # -------------------------------------------------------------------------
    # FI: Lue bytes ja deduplikaatio UploadedFile-tauluun
    # EN: Read bytes and de-duplicate to UploadedFile table
    # -------------------------------------------------------------------------
    if isinstance(file_obj_or_path, str):
        with open(file_obj_or_path, "rb") as fh:
            xml_bytes = fh.read()
    else:
        xml_bytes = file_obj_or_path.read()
    uploaded_file = _ensure_uploaded_file(xml_bytes, uploaded_by=uploaded_by)

    # Jos sama sha256 löytyi, merkitään raporttiin (mutta voidaan jatkaa jos halutaan)
    dedup = UploadedFile.objects.filter(sha256=uploaded_file.sha256).count() > 1

    # -------------------------------------------------------------------------
    # FI: Parsitaan XML
    # EN: Parse the XML
    # -------------------------------------------------------------------------
    root = ET.fromstring(xml_bytes)

    # -------------------------------------------------------------------------
    # FI: Kilpailun perustiedot
    # EN: Competition basics
    # -------------------------------------------------------------------------
    comp_data = _parse_competition(root)
    comp, comp_created = Competition.objects.get_or_create(
        name=comp_data["name"],
        date=comp_data["date"],
        defaults={
            "organizer": comp_data["organizer"],
            "location": comp_data["location"],
            "uploaded_file": uploaded_file,
        },
    )
    if not comp.uploaded_file:
        comp.uploaded_file = uploaded_file
        comp.save(update_fields=["uploaded_file"])

    # -------------------------------------------------------------------------
    # FI: Käydään läpi luokat (ClassResult)
    # EN: Iterate over classes (ClassResult)
    # -------------------------------------------------------------------------
    report = ImportReport(files_deduplicated=dedup)
    if comp_created:
        report.competitions_created += 1

    for class_result in root.findall("iof:ClassResult", NS):
        # Course per class
        course, course_created = _get_or_create_course_for_class(class_result, comp)
        if course_created:
            report.courses_created += 1

        # Athlete + Result + Splits
        athlete, athlete_created = _get_or_create_athlete(class_result)
        if athlete_created:
            report.athletes_created += 1

        result, n_splits = _create_result_and_splits(class_result, course, athlete)
        if result is not None:
            report.results_created += 1
            report.splits_created += n_splits

    report.message = "Import OK"
    return report
