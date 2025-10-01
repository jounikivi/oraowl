# oraw_app/utils/iofxml.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
import hashlib
import re


def parse_time_to_seconds(raw: Optional[str]) -> Optional[int]:
    """
    FI: Muuntaa "hh:mm:ss" / "mm:ss" / "ss" -> sekunnit.
    EN: Convert "hh:mm:ss" / "mm:ss" / "ss" to integer seconds.
    """
    if not raw:
        return None
    raw = raw.strip()
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            h, m, s = [int(p) for p in parts]
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = [int(p) for p in parts]
            return m * 60 + s
        return int(parts[0])
    except ValueError:
        return None


_ws = re.compile(r"\s+")


def clean_text(s: Optional[str]) -> Optional[str]:
    """
    FI: Puhdista whitespace.
    EN: Normalize whitespace.
    """
    if s is None:
        return None
    return _ws.sub(" ", s).strip() or None


def sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """
    FI: Laske tiedoston sha256 (deduplikointiin).
    EN: Compute file sha256 for deduplication.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
