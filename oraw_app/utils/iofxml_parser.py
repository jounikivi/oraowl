# oraw_app/utils/iofxml_parser.py
# ---------------------------------------------------------------
# FI: IOFXML 3.0 ResultList -tiedoston parseri.
# EN: IOFXML 3.0 ResultList parser.
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------
# FI: Datarakenteet, joita parseri palauttaa.
# EN: Data structures returned by the parser.
# ---------------------------------------------------------------

@dataclass
class ParsedSplitTime:
    """
    FI: Yhden rastivälin väliaika.
    EN: Represents one split time entry.
    """
    sequence: int
    control_code: str
    time_seconds: Optional[int]
    status: Optional[str]
    position: Optional[int]


@dataclass
class ParsedAthlete:
    """
    FI: Suunnistaja henkilötietoineen.
    EN: Represents one athlete (person).
    """
    given_name: Optional[str]
    family_name: Optional[str]
    full_name: str
    club_name: Optional[str]
    birth_date: Optional[str]
    gender: Optional[str]
    iof_person_id: Optional[str]


@dataclass
class ParsedCourse:
    """
    FI: Rata tai sarja (pituus, nousu, rastien määrä).
    EN: Represents one course / class.
    """
    name: str
    length_m: Optional[int]
    climb_m: Optional[int]
    controls_count: Optional[int]


@dataclass
class ParsedResult:
    """
    FI: Yksittäisen suunnistajan kilpailutulos.
    EN: One athlete’s result on a specific course.
    """
    athlete: ParsedAthlete
    course: ParsedCourse
    bib_number: Optional[str]
    status: str
    time_seconds: Optional[int]
    position: Optional[int]
    control_card: Optional[str]
    punching_system: Optional[str]
    split_times: list[ParsedSplitTime]


@dataclass
class ParsedClassResult:
    """
    FI: Sarja (esim. H21, D16) sekä kaikki siihen kuuluvat tulokset.
    EN: A class (e.g. H21, D16) with its results.
    """
    class_name: str
    course: ParsedCourse
    results: list[ParsedResult]


@dataclass
class ParsedCompetition:
    """
    FI: Koko kilpailu, jonka IOFXML-tiedosto sisältää.
    EN: Full competition structure contained in the IOFXML document.
    """
    name: str
    date: Optional[str]
    organizer: Optional[str]
    location: Optional[str]
    iof_event_id: Optional[str]
    classes: list[ParsedClassResult]


# ---------------------------------------------------------------
# FI: Sisäiset apufunktiot (nimiavaruudet, tekstit, numerot).
# EN: Internal helper functions (namespaces, text, integers).
# ---------------------------------------------------------------

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


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    """
    FI: Palauta kaikki suorat lapset annetulla paikallisnimellä.
    EN: Return all direct children with a given local-name.
    """
    return [el for el in list(node) if _local(el.tag) == name]


def _text(node: Optional[ET.Element], *path: str) -> Optional[str]:
    """
    FI: Palauta polulla löytyvän elementin teksti tai None.
    EN: Return text of the element at path or None.
    """
    if node is None:
        return None
    el = _first(node, *path) if path else node
    if el is None:
        return None
    val = (el.text or "").strip()
    return val or None


def _int(value: Optional[str]) -> Optional[int]:
    """
    FI: Yritä muuntaa merkkijono kokonaisluvuksi.
    EN: Try to convert a string to an integer.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_athlete(person_result: ET.Element) -> ParsedAthlete:
    """
    FI: Parsii PersonResult-elementistä suunnistajan tiedot.
    EN: Parse athlete data from a PersonResult element.
    """
    person_el = _first(person_result, "Person")
    org_el = _first(person_result, "Organisation")

    given = _text(person_el, "Name", "Given") if person_el is not None else None
    family = _text(person_el, "Name", "Family") if person_el is not None else None
    full = _text(person_el, "Name", "Full") if person_el is not None else None

    if not full:
        parts = [p for p in (given, family) if p]
        full = " ".join(parts) if parts else "Unknown athlete"

    club = None
    if org_el is not None:
        club = _text(org_el, "ShortName") or _text(org_el, "Name")

    birth_date = _text(person_el, "BirthDate") if person_el is not None else None
    gender = _text(person_el, "Sex") if person_el is not None else None
    iof_person_id = _text(person_el, "Id") if person_el is not None else None

    return ParsedAthlete(
        given_name=given,
        family_name=family,
        full_name=full,
        club_name=club,
        birth_date=birth_date,
        gender=gender,
        iof_person_id=iof_person_id,
    )


def _parse_split_times(result_el: ET.Element) -> list[ParsedSplitTime]:
    """
    FI: Parsii Result-elementistä kaikki väliajat.
    EN: Parse all split times from a Result element.
    """
    splits: list[ParsedSplitTime] = []

    for idx, split_el in enumerate(_children(result_el, "SplitTime"), start=1):
        control_code = _text(split_el, "ControlCode") or ""
        time_seconds = _int(_text(split_el, "Time"))
        status = _text(split_el, "Status")
        position = _int(_text(split_el, "Position"))

        splits.append(
            ParsedSplitTime(
                sequence=idx,
                control_code=control_code,
                time_seconds=time_seconds,
                status=status,
                position=position,
            )
        )

    return splits


# ---------------------------------------------------------------
# FI: Julkinen rajapinta (public API).
# EN: Public API.
# ---------------------------------------------------------------

def parse_iofxml_result_list(xml_bytes: bytes) -> ParsedCompetition:
    """
    FI:
        Parsii IOF Data Standard 3.0 ResultList -tiedoston ja palauttaa
        ParsedCompetition-rakenteen. Nimiavaruudet (xmlns) käsitellään
        paikallisnimien avulla. Aikakentät palautetaan sekunteina, jos
        ne ovat valmiiksi kokonaislukuja.

    EN:
        Parse an IOF Data Standard 3.0 ResultList XML document and return
        a ParsedCompetition structure. XML namespaces are handled using
        local-names. Time values are returned as integers (seconds) when
        provided as plain integers in the source.
    """
    # FI: Yritä parsia XML.
    # EN: Try to parse XML.
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    # FI: Tuetut juurielementit (nimialueella ja ilman).
    # EN: Supported root tags (with or without namespace).
    valid_tags = {
        "ResultList",
        "{http://www.orienteering.org/datastandard/3.0}ResultList",
    }

    if root.tag not in valid_tags:
        raise ValueError(
            "FI: Odotettiin <ResultList>-juurielementtiä. "
            "EN: Expected <ResultList> root element.",
        )

    # -----------------------------------------------------------
    # FI: Kilpailun perustiedot (Event).
    # EN: Competition metadata (Event).
    # -----------------------------------------------------------
    event_el = _first(root, "Event")
    if event_el is None:
        raise ValueError(
            "FI: IOFXML ResultList ei sisällä <Event>-elementtiä. "
            "EN: IOFXML ResultList is missing <Event> element.",
        )

    name = _text(event_el, "Name") or "Unknown competition"
    date = _text(event_el, "StartTime", "Date") or _text(
        event_el,
        "StartTime",
        "DateTime",
    )

    organiser_el = _first(event_el, "Organiser") or _first(event_el, "Organizer")
    organizer = None
    if organiser_el is not None:
        organizer = _text(organiser_el, "ShortName") or _text(organiser_el, "Name")

    location = _text(event_el, "Place", "Name")
    iof_event_id = _text(event_el, "Id")

    # -----------------------------------------------------------
    # FI: Sarjat ja tulokset (ClassResult, PersonResult, Result).
    # EN: Classes and results (ClassResult, PersonResult, Result).
    # -----------------------------------------------------------
    classes: list[ParsedClassResult] = []

    for class_result_el in _children(root, "ClassResult"):
        class_name = (
            _text(class_result_el, "Class", "ShortName")
            or _text(class_result_el, "Class", "Name")
            or "Unknown class"
        )

        course_el = _first(class_result_el, "Course")
        if course_el is not None:
            length_m = _int(_text(course_el, "Length"))
            climb_m = _int(_text(course_el, "Climb"))
            controls_count = _int(_text(course_el, "NumberOfControls"))
        else:
            length_m = None
            climb_m = None
            controls_count = None

        course = ParsedCourse(
            name=class_name,
            length_m=length_m,
            climb_m=climb_m,
            controls_count=controls_count,
        )

        results: list[ParsedResult] = []

        for person_result_el in _children(class_result_el, "PersonResult"):
            athlete = _parse_athlete(person_result_el)
            result_el = _first(person_result_el, "Result")
            if result_el is None:
                # FI: Jos tulos puuttuu, ohitetaan tämä PersonResult.
                # EN: If Result element is missing, skip this PersonResult.
                continue

            bib_number = _text(result_el, "BibNumber")
            status = _text(result_el, "Status") or "OK"
            time_seconds = _int(_text(result_el, "Time"))
            position = _int(_text(result_el, "Position"))
            control_card = _text(result_el, "ControlCard")
            punching_system = _text(result_el, "PunchingSystem")

            split_times = _parse_split_times(result_el)

            results.append(
                ParsedResult(
                    athlete=athlete,
                    course=course,
                    bib_number=bib_number,
                    status=status,
                    time_seconds=time_seconds,
                    position=position,
                    control_card=control_card,
                    punching_system=punching_system,
                    split_times=split_times,
                )
            )

        classes.append(
            ParsedClassResult(
                class_name=class_name,
                course=course,
                results=results,
            )
        )

    return ParsedCompetition(
        name=name,
        date=date,
        organizer=organizer,
        location=location,
        iof_event_id=iof_event_id,
        classes=classes,
    )
