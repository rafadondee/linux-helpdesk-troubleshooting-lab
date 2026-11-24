"""Small helper functions shared by all diagnostic modules.

These helpers do not know anything about CPUs, memory or disks.
They only read text files, calculate percentages and format numbers.
Keeping them here means every future module (network, services, ...)
can reuse them.
"""

from __future__ import annotations

from typing import Dict, Optional

# Text shown to the user when a value could not be collected.
UNAVAILABLE = "Unavailable"

# Binary units, the same units used by `free -h` and `df -h`.
_BYTE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")


def read_text_file(path: str) -> Optional[str]:
    """Return the content of a text file, or None if it cannot be read.

    The file is opened in read-only mode ("r"). This tool never writes
    to the system.

    Common reasons for None:
    - the file does not exist (for example /proc on a non-Linux system);
    - the user has no permission to read it.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def parse_key_value_lines(text: str, separator: str) -> Dict[str, str]:
    """Convert lines like "KEY<separator>value" into a dictionary.

    Example with separator "=":
        'NAME="Ubuntu"' -> {"NAME": "Ubuntu"}

    Example with separator ":":
        "MemTotal:  8000000 kB" -> {"MemTotal": "8000000 kB"}

    Empty lines, comment lines (#) and lines without the separator are
    ignored. Surrounding quotes and spaces are removed from values.
    If a key appears more than once, the first value is kept.
    """
    result: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or separator not in line:
            continue
        key, value = line.split(separator, 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in result:
            result[key] = value
    return result


def calculate_percentage(part: Optional[float], total: Optional[float]) -> Optional[float]:
    """Return part / total as a percentage rounded to 1 decimal place.

    Returns None when a value is missing or when total is zero or
    negative, because a percentage of "nothing" has no meaning and
    dividing by zero would crash the program.
    """
    if part is None or total is None or total <= 0:
        return None
    return round(part / total * 100, 1)


def format_bytes(size_in_bytes: Optional[float]) -> str:
    """Convert a number of bytes into a human-readable text.

    Examples:
        512         -> "512 B"
        1536        -> "1.5 KiB"
        8589934592  -> "8.0 GiB"
        None        -> "Unavailable"
    """
    if size_in_bytes is None or size_in_bytes < 0:
        return UNAVAILABLE

    value = float(size_in_bytes)
    for unit in _BYTE_UNITS:
        if value < 1024 or unit == _BYTE_UNITS[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return UNAVAILABLE  # pragma: no cover - loop always returns


def format_duration(total_seconds: Optional[float]) -> str:
    """Convert seconds into text like "2 days, 3 hours, 15 minutes".

    Seconds are not shown because uptime is usually measured in
    minutes, hours or days. Values under one minute show "less than
    1 minute".
    """
    if total_seconds is None or total_seconds < 0:
        return UNAVAILABLE

    minutes_total = int(total_seconds // 60)
    days, remainder = divmod(minutes_total, 24 * 60)
    hours, minutes = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts) if parts else "less than 1 minute"


def format_percentage(value: Optional[float]) -> str:
    """Format a percentage value, for example 42.5 -> "42.5%"."""
    if value is None:
        return UNAVAILABLE
    return f"{value:.1f}%"


def display_value(value: object) -> str:
    """Return the value as text, or "Unavailable" when it is None or empty."""
    if value is None or value == "":
        return UNAVAILABLE
    return str(value)
