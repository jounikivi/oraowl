# oraw_app/utils/iofxml_importer.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional, Tuple

from django.db import transaction

from oraw_app.models import (
    Competition,
    Course,
    Athlete,
    Result,
    Split,
    UploadedFile,
    ControlCard,
)
from .iofxml import parse_time_to_seconds, clean_text


# --------------------------------------------------------------------
# FI: IOF v3 käyttää usein default-namespacen (xmlns="..."), jolloin
#     pelkkä find("Event") ei löydä mitään. Alla helperit, jotka
#     kvalifioivat tagit aktiivisella nimialueella.
# EN: IOF v3 often has a default namespace, so find("Event") won't
#     match. Helpers below qualify tags with the active namespace.
# --------------------------------------------------------------------

def _ns_url_from_tag(tag: str) -> Optional[str]:
    # "{namespace}ResultList" -> "namespace"
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return None


NS_URL: Optional[str] = None  # set per import


def _qn(name: str) -> str:
    # Qualify one name with namespace, if present.
    return f"{{{NS_URL}}}{name}" if NS_URL else name


def _p(*names: str) -> str:
    # Build a path "A/B/C" with each part qualified.
    return "/".join(_qn(n) for n in names)


# --------------------------------------------------------------------
# Simple XML helpers
# --------------------------------------------------------------------

def _text(el: Optional[ET.Element], *path: str) -> Optional[str]:
    """
    FI: Palauta polun teksti nimialue huomioiden.
    EN: Return text at namespaced path.
    """
    if el is None:
        return None
    found = el.find(_p(*path))
    return clean_text(found.text if found is not None else None)


def _attr(el: Optional[ET.Element], first: str, attr: str, *rest: str) -> Optional[str]:
    """
    FI: Palauta polun attribuutti nimialue huomioiden.
    EN: Return attribute value at namespaced path.
    """
    if el is None:
        return None
    found = el.find(_p(first, *rest))
    return clean_text(found.get(attr) if found is not None else None)


def _length_to_km(length_text: Optional[str], unit: Optional[str]) -> Optional[float]:
    """
    FI: Muunna IOFXML Course/Length arvo kilometreiksi. Unit voi olla 'm' tai 'km'.
    EN: Convert Course/Length to kilometers. Unit may be 'm' or 'km'.
    """
    if not length_text:
        return None
    try:
        val = float(length_text)
    except ValueError:
        return None
    unit = (unit or "").lower()
    if unit == "m":
        return round(val / 1000.0, 2)
    return round(val, 2)  # assume km if not specified


# --------------------------------------------------------------------
# Importer core
# --------------------------------------------------------------------

@transaction.atomic
def import_result_list(
    xml_bytes: bytes,
    source_file: Optional[UploadedFile],
) -> Tuple[Competition, int, int]:
    """
    FI: Tuo IOF v3 ResultList-XML:n. Linkitä Competition -> source_file, jos annettu.
    EN: Import IOF v3 ResultList XML. Link Competition -> source_file if provided.
    Returns: (Competition, athletes_created, results_created).
    """
    root = ET.fromstring(xml_bytes)

    # Set namespace for this import
    global NS_URL
    NS_URL = _ns_url_from_tag(root.tag)

    # 1) Competition / Event
    event_el = root.find(_p("Event"))
    comp_name = _text(event_el, "Name") or "Unnamed event"
    comp_date = _text(event_el, "StartTime", "Date")  # YYYY-MM-DD
    organizer = (
    _text(event_el, "Organizer", "Name")
    or _text(event_el, "Organiser", "Name")
)

    location = _text(event_el, "Place")

    competition, _ = Competition.objects.get_or_create(
        name=comp_name,
        date=comp_date or None,
        defaults={"organizer": organizer, "location": location},
    )
    if source_file and not competition.source_file:
        competition.source_file = source_file
        competition.save(update_fields=["source_file"])

    # 2) ClassResult -> Course
    class_results = root.findall(_p("ClassResult"))
    athletes_created = 0
    results_created = 0

    for class_res in class_results:
        class_name = _text(class_res, "Class", "Name") or "Unknown"

        # Optional course length
        length_text = _text(class_res, "Course", "Length")
        length_unit = _attr(class_res, "Course", "Length", "unit")
        length_km = _length_to_km(length_text, length_unit)

        course, _ = Course.objects.get_or_create(
            competition=competition,
            name=class_name,
            defaults={"clazz": class_name, "length_km": length_km},
        )
        if course.length_km is None and length_km is not None:
            course.length_km = length_km
            course.save(update_fields=["length_km"])

        # 3) PersonResult -> Athlete + Result (+ Splits)
        for pr in class_res.findall(_p("PersonResult")):
            first = _text(pr, "Person", "Name", "Given") or ""
            last = _text(pr, "Person", "Name", "Family") or ""
            club = _text(pr, "Organisation", "Name")
            gender = _text(pr, "Person", "Sex")
            gender = (gender_raw or "").strip().upper()
            if gender not in {"M", "F"}:
                gender = "X"
            defaults={"club": club, "gender": gender},
            
            

            athlete, created_a = Athlete.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={"club": club, "gender": (gender or "").upper()[:1]},
            )
            if created_a:
                athletes_created += 1

            for r in pr.findall(_p("Result")):
                time_s = parse_time_to_seconds(_text(r, "Time"))
                status = _text(r, "Status") or "UNK"
                pos_text = _text(r, "Position")
                position = int(pos_text) if (pos_text and pos_text.isdigit()) else None

                # ---- ControlCard (optional) ---------------------------------
                card_uid = _text(r, "ControlCard")
                card = None
                if card_uid:
                    # FI: Oletetaan vendor tuntemattomaksi; voidaan laajentaa heuristiikalla.
                    # EN: Default vendor as UNKNOWN; can refine with heuristics later.
                    card, _ = ControlCard.objects.get_or_create(
                        vendor=ControlCard.UNKNOWN,
                        uid=card_uid,
                    )

                # Upsert result
                result, created_r = Result.objects.update_or_create(
                    course=course,
                    athlete=athlete,
                    defaults={
                        "finish_time_s": time_s,
                        "status": status,
                        "position": position,
                        "control_card": card,
                    },
                )
                if created_r:
                    results_created += 1

                # Splits: re-create for MVP simplicity
                result.splits.all().delete()
                last_cum = None
                seq = 0
                for st in r.findall(_p("SplitTime")):
                    seq += 1
                    code = _text(st, "ControlCode")
                    cum = parse_time_to_seconds(_text(st, "Time"))
                    leg = (
                        cum - last_cum
                        if (cum is not None and last_cum is not None)
                        else cum
                    )
                    Split.objects.create(
                        result=result,
                        seq=seq,
                        control_code=code,
                        time_s=cum or 0,
                        leg_time_s=leg or 0,
                    )
                    last_cum = cum

    return competition, athletes_created, results_created
