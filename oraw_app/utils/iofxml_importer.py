"""
oraw_app/utils/iofxml_importer.py

FI: IOF v3 (ResultList XML) -tiedoston tuonti tietokantaan.
EN: Importer for IOF v3 (ResultList XML) data into the database.

Rules:
- Code in English, bilingual comments (FI/EN)
- Readable, modular, GDPR-ready
"""

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

# ============================================================
# 🔧 Namespace helpers
# ============================================================

def _ns_url_from_tag(tag: str) -> Optional[str]:
    """Extract namespace from tag: '{namespace}ResultList' -> 'namespace'."""
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return None


NS_URL: Optional[str] = None


def _qn(name: str) -> str:
    """Qualify tag name with namespace."""
    return f"{{{NS_URL}}}{name}" if NS_URL else name


def _p(*names: str) -> str:
    """Build a qualified XML path A/B/C."""
    return "/".join(_qn(n) for n in names)


# ============================================================
# 🧩 XML helpers
# ============================================================

def _text(el: Optional[ET.Element], *path: str) -> Optional[str]:
    """FI: Palauta teksti polusta. EN: Return text at namespaced path."""
    if el is None:
        return None
    found = el.find(_p(*path))
    return clean_text(found.text if found is not None else None)


def _attr(el: Optional[ET.Element], first: str, attr: str, *rest: str) -> Optional[str]:
    """FI: Palauta attribuutti. EN: Return attribute value."""
    if el is None:
        return None
    found = el.find(_p(first, *rest))
    return clean_text(found.get(attr) if found is not None else None)


def _length_to_km(length_text: Optional[str], unit: Optional[str]) -> Optional[float]:
    """FI: Muunna metri/kilometri -> km. EN: Convert meters/kilometers -> km."""
    if not length_text:
        return None
    try:
        val = float(length_text)
    except ValueError:
        return None
    unit = (unit or "").lower()
    if unit == "m":
        return round(val / 1000.0, 2)
    return round(val, 2)


def _norm_gender(value: Optional[str]) -> Optional[str]:
    """FI: Normalisoi sukupuolikoodi. EN: Normalize gender value."""
    if not value:
        return None
    v = value.strip().upper()
    if v in {"M", "MALE"}:
        return "M"
    if v in {"F", "FEMALE", "W"}:
        return "F"
    return None


# ============================================================
# 📥 Main importer
# ============================================================

@transaction.atomic
def import_result_list(
    xml_bytes: bytes,
    source_file: Optional[UploadedFile],
) -> Tuple[Competition, int, int]:
    """
    FI: Tuo IOF v3 ResultList XML ja tallenna tietokantaan.
    EN: Import IOF v3 ResultList XML into database.

    Returns:
        (Competition, athletes_created, results_created)
    """
    root = ET.fromstring(xml_bytes)

    # Activate namespace
    global NS_URL
    NS_URL = _ns_url_from_tag(root.tag)

    # --- 1) Competition ---
    event_el = root.find(_p("Event"))
    comp_name = _text(event_el, "Name") or "Unnamed event"
    comp_date = _text(event_el, "StartTime", "Date")
    organizer = _text(event_el, "Organizer", "Name") or _text(event_el, "Organiser", "Name")
    location = _text(event_el, "Place")

    competition, _ = Competition.objects.get_or_create(
        name=comp_name,
        date=comp_date or None,
        defaults={"organizer": organizer, "location": location},
    )
    if source_file and not competition.source_file:
        competition.source_file = source_file
        competition.save(update_fields=["source_file"])

    # --- 2) Course & Class ---
    class_results = root.findall(_p("ClassResult"))
    athletes_created = 0
    results_created = 0

    for class_res in class_results:
        class_name = _text(class_res, "Class", "Name") or "Unknown"

        length_text = _text(class_res, "Course", "Length")
        length_unit = _attr(class_res, "Course", "unit", "Length")
        length_km = _length_to_km(length_text, length_unit)

        course, _ = Course.objects.get_or_create(
            competition=competition,
            name=class_name,
            defaults={"length_km": length_km},
        )
        if course.length_km is None and length_km is not None:
            course.length_km = length_km
            course.save(update_fields=["length_km"])

        # --- 3) Athletes, Results, Splits ---
        for pr in class_res.findall(_p("PersonResult")):
            first = _text(pr, "Person", "Name", "Given") or ""
            last = _text(pr, "Person", "Name", "Family") or ""
            club = _text(pr, "Organisation", "Name")
            gender = _norm_gender(_text(pr, "Person", "Sex"))

            athlete, created_a = Athlete.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={"club": club, "gender": gender},
            )
            if created_a:
                athletes_created += 1

            for r in pr.findall(_p("Result")):
                time_s = parse_time_to_seconds(_text(r, "Time"))
                status = _text(r, "Status") or "UNK"
                pos_text = _text(r, "Position")
                position = int(pos_text) if pos_text and pos_text.isdigit() else None

                # --- Control card ---
                card_uid = _text(r, "ControlCard")
                card = None
                if card_uid:
                    card, _ = ControlCard.objects.get_or_create(
                        vendor=ControlCard.VENDOR_UNKNOWN,
                        uid=card_uid,
                    )

                # --- Result ---
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

                # --- Splits ---
                result.splits.all().delete()
                last_cum = 0
                seq = 0
                for st in r.findall(_p("SplitTime")):
                    seq += 1
                    ctrl_code = _text(st, "ControlCode") or f"UNK{seq}"
                    cum_time = parse_time_to_seconds(_text(st, "Time")) or 0
                    leg_time = cum_time - last_cum if last_cum else cum_time

                    Split.objects.create(
                        result=result,
                        seq=seq,
                        control_code=ctrl_code,
                        split_time_s=leg_time,
                        cum_time_s=cum_time,
                    )
                    last_cum = cum_time

    return competition, athletes_created, results_created
