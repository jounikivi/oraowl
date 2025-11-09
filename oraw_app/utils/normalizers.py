from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Optional

# ============================================================================
# FI: Tähän kerätään kaikki arvojen turvalliset parsimiset IOFXML:ää varten.
# EN: Safe parsers for IOFXML values live here.
# ============================================================================

DASH_VALUES = {"", "-", "–", "—", "—", "—".replace("\u2014", "-")}  # normalize dashes


def _is_dashy(value: str) -> bool:
    """
    FI: Palauttaa True jos arvo on tyhjä tai sisältää viivan tms.
    EN: Returns True if the value is empty/dashy.
    """
    s = (value or "").strip()
    return s in DASH_VALUES


def parse_decimal(value: object) -> Optional[Decimal]:
    """
    FI: Yleinen turvallinen Decimal-parseri. Hyväksyy myös desimaalipilkun.
    EN: Safe Decimal parser; accepts comma as decimal separator as well.
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
    FI: Turvallinen kokonaisluvun parsinta (dashy -> None).
    EN: Safe integer parsing (dashy -> None).
    """
    if value is None:
        return None
    s = str(value).strip()
    if _is_dashy(s):
        return None
    try:
        return int(s)
    except ValueError:
        # joskus tulee "5600.0" -> yritetään Decimalin kautta
        d = parse_decimal(s)
        return int(d) if d is not None else None


def parse_length_km_from_meters(value: object) -> Optional[Decimal]:
    """
    FI: IOFXML:n Course.Length on metreinä. Muunna kilometreiksi (3 desimaalia).
        Palauta None jos arvo on kelvoton.
    EN: IOFXML Course.Length is meters. Convert to kilometers (3 decimals).
        Return None if invalid.
    """
    meters = parse_decimal(value)
    if meters is None:
        return None
    km = meters / Decimal(1000)
    # 0.001 precision is enough (e.g., 5600m -> 5.600 km)
    return km.quantize(Decimal("0.001"))


def parse_climb_m(value: object) -> Optional[int]:
    """
    FI: Noustut metrit (Climb) kokonaislukuna. Kelvoton -> None.
    EN: Climb in meters as integer. Invalid -> None.
    """
    return parse_int(value)


def parse_time_to_seconds(value: object) -> Optional[int]:
    """
    FI: Muuntaa ajan sekunneiksi. Tukee "HH:MM:SS", "MM:SS", pelkät sekunnit (int/str).
        Kelvoton tai tyhjä -> None.
    EN: Converts time into seconds. Supports "HH:MM:SS", "MM:SS",
        and integer seconds. Invalid/empty -> None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if _is_dashy(s):
        return None

    # plain integer seconds?
    if s.isdigit():
        return int(s)

    # split by colon
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

    # fallback: decimal seconds (e.g., "75.2")
    dec = parse_decimal(s)
    if dec is not None:
        return int(dec)  # truncate fractional part

    return None


def normalize_status(iof_status: str) -> str:
    """
    FI: Normalisoi IOF-statuksen. Yhtenäistetään Result.status-kenttää varten.
    EN: Normalize IOF status for consistent Result.status storage.
    """
    s = (iof_status or "").strip().lower()
    mapping = {
        "ok": "OK",
        "ok result": "OK",
        "didnotstart": "DNS",
        "did not start": "DNS",
        "dns": "DNS",
        "didnotfinish": "DNF",
        "did not finish": "DNF",
        "dnf": "DNF",
        "missingpunch": "MP",
        "missing punch": "MP",
        "mp": "MP",
        "disqualified": "DSQ",
        "dsq": "DSQ",
        "retired": "DNF",
        "overmaximumbogus": "DSQ",  # esimerkki: tuntemattomat voidaan mapata DSQ:ksi
    }
    return mapping.get(s, "OK")
