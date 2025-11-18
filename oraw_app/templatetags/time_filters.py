# oraw_app/templatetags/time_filters.py
from __future__ import annotations

from typing import Any, Optional

from django import template

register = template.Library()


def _format_seconds_to_string(value: int) -> str:
    """
    FI:
        Apufunktio, joka muuntaa sekuntimäärän merkkijonoksi.
        - alle tunnin ajat:   mm:ss (esim. 45:03)
        - tunnin tai pidemmät: h:mm:ss (esim. 1:05:30)

    EN:
        Helper that converts a number of seconds into a time string.
        - times under one hour:   mm:ss (e.g. 45:03)
        - times of one hour or more: h:mm:ss (e.g. 1:05:30)
    """
    if value < 0:
        # FI: Negatiivisia aikoja ei pitäisi tulla, mutta varmuuden vuoksi.
        # EN: Negative times should not occur, but guard just in case.
        value = 0

    hours = value // 3600
    minutes = (value % 3600) // 60
    seconds = value % 60

    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:d}:{seconds:02d}"


@register.filter(name="format_seconds")
def format_seconds(value: Any) -> str:
    """
    FI:
        Django-templatefilter, joka muuntaa sekuntimäärän luettavaan
        aikaformaattiin:
            75   -> "1:15"
            3661 -> "1:01:01"

        Jos arvo on tyhjä/None tai ei muunnettavissa kokonaisluvuksi,
        palautetaan "-".

    EN:
        Django template filter that formats a number of seconds into a
        human-readable time string:
            75   -> "1:15"
            3661 -> "1:01:01"

        If the value is empty/None or cannot be converted to an integer,
        "-" is returned.
    """
    if value is None or value == "":
        return "-"

    try:
        seconds_int = int(value)
    except (TypeError, ValueError):
        return "-"

    return _format_seconds_to_string(seconds_int)
