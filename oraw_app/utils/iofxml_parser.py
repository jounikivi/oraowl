# oraw_app/utils/iofxml_parser.py
# ---------------------------------------------------------------
# FI: IOFXML 3.0 ResultList -tiedoston parseri (luuranko)
# EN: IOFXML 3.0 ResultList parser (skeleton implementation)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------
# FI: Datarakenteet, joita parseri palauttaa
# EN: Data structures returned by the parser
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
    EN: Represents one athlete’s result on a specific course.
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
    EN: Represents a class (e.g., H21, D16) with its results.
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
# FI: Julkinen rajapinta (public API)
# EN: Public API
# ---------------------------------------------------------------

def parse_iofxml_result_list(xml_bytes: bytes) -> ParsedCompetition:
    """
    FI:
        Parsii IOF Data Standard 3.0 ResultList -tiedoston.
        Tämä versio tarkistaa vain rakenteen. Varsinainen
        tietojen poiminta toteutetaan seuraavassa vaiheessa.

    EN:
        Parse an IOF Data Standard 3.0 ResultList XML document.
        This skeleton only validates the structure. Actual data
        extraction will be implemented in the next step.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    # FI: Tuetut juurielementit (nimialueella ja ilman)
    # EN: Supported root tags (with or without namespace)
    valid_tags = {
        "ResultList",
        "{http://www.orienteering.org/datastandard/3.0}ResultList",
    }

    if root.tag not in valid_tags:
        raise ValueError(
            "FI: Odotettiin <ResultList>-juurielementtiä. "
            "EN: Expected <ResultList> root element."
        )

    # FI: Varsinainen Event/ClassResult/Result/SplitTime-parsinta lisätään myöhemmin.
    # EN: Actual parsing of Event/ClassResult/Result/SplitTime is added later.
    raise NotImplementedError("FI/EN: IOFXML parsing not yet implemented.")
