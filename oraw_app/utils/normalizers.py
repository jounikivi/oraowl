from __future__ import annotations

"""
FI: Normalisointiapurit IOFXML-datalle. Kaikki "oikeasta kisadatasta" tulevien
    arvojen turvalliset parsinnat keskitetty tänne (Decimal, ajat, statukset).
EN: Normalization helpers for IOFXML data. Safe parsing for real-world race data
    (decimals, times, statuses) are centralized here.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


# -----------------------------------------------------------------------------
# FI: Tyhjiä/viivamaisia arvoja, jotka tulkitaan 'puuttuviksi'.
# EN: Empty/dashy values that are treated as "missing".
# -----------------------------------------------------------------------------
DASH_VALUES = {"", "-", "–", "—"}


def _is_dashy(value: str) -> bool:
    """
    FI: Palauttaa True jos arvo on tyhjä tai jokin viivamerkki.
    EN: Returns True if the value is empty or a dash variant.
    """
    s = (value or "").strip()
    return s in DASH_VALUES


def parse_decimal(value: object) -> Optional[Decimal]:
    """
    FI: Turvallinen Decimal-parsinta. Ymmärtää myös desimaalipilkun.
    EN: Safe Decimal parser. Accepts comma as decimal separator too.
    """
    if value is None:
        return None
    s = str(value).strip()
    if _is_dashy(s):
        return None
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: object) -> Optional[int]:
    """
    FI: Turvallinen kokonaisluvun parsinta (myös "5600.0" -> 5600).
    EN: Safe integer parsing (also handles "5600.0" -> 5600).
    """
    if value is None:
        return None
    s = str(value).strip()
    if _is_dashy(s):
        return None
    try:
        return int(s)
    except ValueError:
        d = parse_decimal(s)
        return int(d) if d is not None else None


def parse_length_km_from_meters(value: object) -> Optional[Decimal]:
    """
    FI: IOFXML Course.Length on metreinä. Muunna kilometreiksi (3 desimaalia).
        Palauta None jos arvo on kelvoton.
    EN: IOFXML Course.Length is in meters. Convert to kilometers (3 decimals).
        Return None if invalid.
    """
    meters = parse_decimal(value)
    if meters is None:
        return None
    km = meters / Decimal(1000)
    return km.quantize(Decimal("0.001"))


def parse_climb_m(value: object) -> Optional[int]:
    """
    FI: Nousu metreinä (Climb). Kelvoton -> None.
    EN: Climb in meters (integer). Invalid -> None.
    """
    return parse_int(value)


def parse_time_to_seconds(value: object) -> Optional[int]:
    """
    FI: Muuntaa ajan sekunneiksi. Tukee "HH:MM:SS", "MM:SS", pelkät sekunnit
        (int/str) sekä desimaalit sekunteina ("75.3" -> 75).
        Kelvoton tai tyhjä -> None.
    EN: Converts time into seconds. Supports "HH:MM:SS", "MM:SS",
        integer seconds (int/str) and decimal seconds ("75.3" -> 75).
        Invalid/empty -> None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if _is_dashy(s):
        return None

    # plain integer seconds?
    if s.isdigit():
        return int(s)

    parts = s.split(":")
    try:
        if len(parts) == 2:  # MM:SS
            mm, ss = parts
            return int(mm) * 60 + int(ss)
        if len(parts) == 3:  # HH:MM:SS
            hh, mm, ss = parts
            return int(hh) * 3600 + int(mm) * 60 + int(ss)
    except ValueError:
        return None

    dec = parse_decimal(s)
    if dec is not None:
        return int(dec)
    return None


def normalize_status(iof_status: str) -> str:
    """
    FI: Normalisoi IOF-statuksen. Palauttaa yhdenmukaiset arvot (OK, DNS, DNF,
        MP, DSQ). Tuntemattomat mapataan OK:ksi ellei haluta DSQ/DNF oletusta.
    EN: Normalize IOF status to a consistent set (OK, DNS, DNF, MP, DSQ).
        Unknown maps to OK (change if you prefer DSQ/DNF as default).
    """
    s = (iof_status or "").strip().lower()
    mapping = {
        "ok": "OK",
        "ok result": "OK",
        "dns": "DNS",
        "didnotstart": "DNS",
        "did not start": "DNS",
        "dnf": "DNF",
        "didnotfinish": "DNF",
        "did not finish": "DNF",
        "missingpunch": "MP",
        "missing punch": "MP",
        "mp": "MP",
        "disqualified": "DSQ",
        "dsq": "DSQ",
        "retired": "DNF",
    }
    return mapping.get(s, "OK")
