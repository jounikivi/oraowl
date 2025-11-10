# oraw_app/utils/iofxml_importer.py
"""
FI: IOFXML ResultList -tuonnin apukirjasto ORAOwl-projektille.
    - Parsii kilpailun, radat, urheilijat, tulokset ja väliajat.
    - Tallentaa alkuperäisen XML:n UploadedFile-malliin (deduplikointi sha256).
    - HUOM: Nimiavaruus (xmlns) tuettu ja ratojen pituus käsitellään Decimal-arvoina.

EN: Helper module for importing IOFXML ResultList into ORAOwl.
    - Parses competition, courses, athletes, results and splits.
    - Stores the original XML into UploadedFile (sha256 dedupe).
    - NOTE: XML namespaces are supported and course length uses Decimals.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Tuple, List
from xml.etree import ElementTree as ET

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

# ============================================================================
# XML helpers (namespace-agnostic) / XML-apurit (nimiavaruus-agnostinen)
# ============================================================================

def _local(tag: str) -> str:
    """
    FI: Palauta tägin paikallisnimi (ilman nimiavaruutta).
    EN: Return the element's local-name (without namespace).
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _first(node: ET.Element, *path: str) -> Optional[ET.Element]:
    """
    FI: Etsi ketjutettuna ensimmäinen lapsi kustakin tasosta paikallisnimellä.
    EN: Walk down by local-name and return the first matching child at each step.
    """
    cur = node
    for name in path:
        found = None
        for child in list(cur):
            if _local(child.tag) == name:
                found = child
                break
        if found is None:
            return None
        cur = found
    return cur


def _children(node: ET.Element, name: str) -> List[ET.Element]:
    """
    FI: Palauta kaikki suorat lapset annetulla paikallisnimellä.
    EN: Return all direct children with a given local-name.
    """
    return [el for el in list(node) if _local(el.tag) == name]


def _text(node: ET.Element, *path: str) -> Optional[str]:
    """
    FI: Palauta polulla löytyvän elementin teksti tai None.
    EN: Return text of the element at path or None.
    """
    el = _first(node, *path)
    if el is None:
        return None
    val = (el.text or "").strip()
    return val or None


def _attr(node: ET.Element, *path: str) -> Optional[str]:
    """
    FI: Palauta viimeisen polkuosion attribuuttiarvo (… , 'attrname').
    EN: Return attribute value of the last path segment (… , 'attrname').
    """
    *elem_path, attr_name = path
    el = _first(node, *elem_path) if elem_path else node
    if el is None:
        return None
    val = el.get(attr_name)
    if val is None:
        return None
    val = val.strip()
    return val or None


# ============================================================================
# Length normalization / Pituuden normalisointi
# ============================================================================

def _length_to_km(length_text: Optional[str], unit: Optional[str]) -> Optional[float]:
    """
    FI: Muunna metreistä/kilometreistä kilometreiksi (float) tai palauta None.
    EN: Convert metres/kilometres to kilometres (float) or return None.
    """
    if length_text is None:
        return None
    s = length_text.strip().replace(",", ".")
    if not s:
        return None
    try:
        value = float(s)
    except ValueError:
        return None

    u = (unit or "").strip().lower()
    if u in {"km", "kilometer", "kilometre", "kilometres", "kilometers"}:
        return value
    if u in {"m", "meter", "metre", "meters", "metres"}:
        return value / 1000.0
    # Unknown unit → assume km
    return value


def _length_to_decimal_km(length_text: Optional[str], unit: Optional[str]) -> Optional[Decimal]:
    """
    FI: Muunna pituus Decimal-kilometreiksi turvallisesti (tai None).
    EN: Safely convert length to Decimal kilometres (or None).
    """
    km_float = _length_to_km(length_text, unit)
    if km_float is None:
        return None
    try:
        return Decimal(str(km_float))  # avoid float artefacts
    except InvalidOperation:
        return None


# ============================================================================
# Core import / Tuonnin ydin
# ============================================================================

@dataclass
class ImportReport:
    competitions_created: int = 0
    courses_created: int = 0
    athletes_created: int = 0
    results_created: int = 0
    splits_created: int = 0
    control_cards_created: int = 0
    uploaded_file: Optional[UploadedFile] = None


def _sha256_bytes(payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(payload)
    return h.hexdigest()


def _parse_competition(root: ET.Element) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    FI: Palauttaa kilpailun perustiedot: nimi, päivä (YYYY-MM-DD), järjestäjä, paikka.
    EN: Return basic competition info: name, date (YYYY-MM-DD), organizer, place.
    """
    name = _text(root, "Event", "Name") or "Unnamed competition"
    date = _text(root, "Event", "StartTime", "Date")
    organizer = _text(root, "Event", "Organizer", "Name")
    place = _text(root, "Event", "City")
    return name, date, organizer, place


@transaction.atomic
def import_result_list(*, file_bytes: bytes, filename: str) -> ImportReport:
    """
    FI: Tuo IOFXML ResultList -datan bytes-muodossa. Tallentaa UploadedFileen ja
        rakentaa Competition/Course/Athlete/Result/Split/ControlCard -rivit.
    EN: Import IOFXML ResultList from bytes. Stores in UploadedFile and creates
        Competition/Course/Athlete/Result/Split/ControlCard rows.
    """
    report = ImportReport()

    # --- Store (or dedupe) original XML -------------------------------------
    sha256 = _sha256_bytes(file_bytes)
    uploaded, created = UploadedFile.objects.get_or_create(
        sha256=sha256,
        defaults={
            "original_name": filename,
            "content": file_bytes,
            "uploaded_at": timezone.now(),
        },
    )
    report.uploaded_file = uploaded
    # importer is idempotent; we continue even if duplicate

    # --- Parse XML -----------------------------------------------------------
    root = ET.fromstring(file_bytes)

    # --- Competition ---------------------------------------------------------
    comp_name, comp_date, comp_org, comp_place = _parse_competition(root)
    competition, created = Competition.objects.get_or_create(
        name=comp_name,
        date=comp_date,
        defaults={
            "organizer": comp_org,
            "place": comp_place,
            "uploaded_file": uploaded,
        },
    )
    if created:
        report.competitions_created += 1

    # --- ResultList: Classes -> Courses, Persons -> Results/Splits -----------
    # Namespace-agnostic selection:
    class_results: List[ET.Element] = _children(root, "ClassResult")

    for class_res in class_results:
        # Course
        class_name = _text(class_res, "Class", "Name") or "Unnamed course"
        length_text = _text(class_res, "Course", "Length")
        length_unit = _attr(class_res, "Course", "Length", "unit")
        length_km = _length_to_decimal_km(length_text, length_unit)

        course, c_created = Course.objects.get_or_create(
            competition=competition,
            name=class_name,
            defaults={"length_km": length_km},
        )
        if c_created:
            report.courses_created += 1
        elif course.length_km is None and length_km is not None:
            course.length_km = length_km
            course.save(update_fields=["length_km"])

        # PersonResult[]
        person_results: List[ET.Element] = _children(class_res, "PersonResult")
        for person_res in person_results:
            # Athlete
            given = _text(person_res, "Person", "Name", "Given") or ""
            family = _text(person_res, "Person", "Name", "Family") or ""
            full_name = (given + " " + family).strip() or "Unknown athlete"
            club = _text(person_res, "Organisation", "Name")

            # Optional birth year
            birth = _text(person_res, "Person", "BirthDate")
            birth_year = None
            if birth and len(birth) >= 4 and birth[:4].isdigit():
                birth_year = int(birth[:4])

            athlete, a_created = Athlete.objects.get_or_create(
                full_name=full_name,
                defaults={
                    "club": club,
                    "birth_year": birth_year,
                    "is_public": True,
                    "public_alias": None,
                },
            )
            if a_created:
                report.athletes_created += 1

            # Control card (optional)
            card_vendor = _attr(person_res, "Result", "ControlCard", "vendor")
            card_uid = _text(person_res, "Result", "ControlCard")
            control_card = None
            if card_vendor and card_uid:
                control_card, cc_created = ControlCard.objects.get_or_create(
                    vendor=card_vendor, uid=card_uid
                )
                if cc_created:
                    report.control_cards_created += 1

            # Result
            status = _text(person_res, "Result", "Status") or "OK"
            time_s_text = _text(person_res, "Result", "Time")
            time_seconds = int(time_s_text) if (time_s_text and time_s_text.isdigit()) else None
            place_text = _text(person_res, "Result", "Position")
            place = int(place_text) if (place_text and place_text.isdigit()) else None

            result, r_created = Result.objects.get_or_create(
                athlete=athlete,
                course=course,
                defaults={
                    "status": status,
                    "time_seconds": time_seconds,
                    "position": place,
                    "control_card": control_card,
                },
            )
            if r_created:
                report.results_created += 1
            else:
                fields_to_update = []
                if result.status != status:
                    result.status = status
                    fields_to_update.append("status")
                if result.time_seconds is None and time_seconds is not None:
                    result.time_seconds = time_seconds
                    fields_to_update.append("time_seconds")
                if result.position is None and place is not None:
                    result.position = place
                    fields_to_update.append("position")
                if result.control_card is None and control_card is not None:
                    result.control_card = control_card
                    fields_to_update.append("control_card")
                if fields_to_update:
                    result.save(update_fields=fields_to_update)

            # Splits (optional)
            result_node = _first(person_res, "Result")
            split_nodes: List[ET.Element] = _children(result_node, "SplitTime") if result_node is not None else []
            seq = 1
            cum = 0
            for sp in split_nodes:
                code = _text(sp, "ControlCode")
                sp_time_text = _text(sp, "Time")
                sp_time = int(sp_time_text) if (sp_time_text and sp_time_text.isdigit()) else None
                if sp_time is None:
                    continue
                cum += sp_time
                Split.objects.create(
                    result=result,
                    sequence=seq,
                    control_code=code or "",
                    split_time_seconds=sp_time,
                    cumulative_time_seconds=cum,
                )
                report.splits_created += 1
                seq += 1

    return report
