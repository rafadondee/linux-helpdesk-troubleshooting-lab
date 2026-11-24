"""MODULE 01 - System information.

This module collects basic information about a Linux computer:
operating system, kernel, hostname, CPU, memory, disk and uptime.

Design rules for this module:
- Read-only: files are only opened for reading. Nothing is changed.
- No root needed: every source used here is readable by normal users.
- No external packages: only the Python standard library is used.
- Graceful failure: if one value cannot be collected, it becomes
  None and a warning is recorded. The rest of the report still works.

Where the information comes from:
    Distribution  -> /etc/os-release        (same as: cat /etc/os-release)
    Kernel        -> uname system call      (same as: uname -r)
    Hostname      -> gethostname()          (same as: hostname)
    CPU model     -> /proc/cpuinfo          (same as: lscpu)
    Logical cores -> os.cpu_count()         (same as: nproc --all)
    Memory        -> /proc/meminfo          (same as: free -b)
    Disk          -> statvfs() system call  (same as: df -B1 /)
    Uptime        -> /proc/uptime           (same as: uptime -p)
"""

from __future__ import annotations

import datetime
import os
import platform
import shutil
import socket
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import __version__
from .utils import calculate_percentage, parse_key_value_lines, read_text_file

# File locations. They are constants so tests can replace them with
# temporary files, and so readers can see every source in one place.
OS_RELEASE_PATHS: Sequence[str] = ("/etc/os-release", "/usr/lib/os-release")
CPUINFO_PATH = "/proc/cpuinfo"
MEMINFO_PATH = "/proc/meminfo"
UPTIME_PATH = "/proc/uptime"
DEFAULT_DISK_PATH = "/"

# /proc/meminfo reports values in kibibytes (it writes "kB", but the
# kernel really means 1024 bytes).
BYTES_PER_KIB = 1024

# Keys used by different CPU architectures in /proc/cpuinfo.
# x86/x86_64 use "model name"; some ARM boards use "Model" or "Hardware".
_CPU_MODEL_KEYS = ("model name", "Model", "Hardware", "Processor", "cpu model")


# ---------------------------------------------------------------------------
# Operating system
# ---------------------------------------------------------------------------

def get_distribution_info(os_release_paths: Sequence[str] = OS_RELEASE_PATHS) -> Dict[str, Optional[str]]:
    """Read the Linux distribution name and version from os-release.

    /etc/os-release is a standard text file found on almost every modern
    Linux distribution. Example lines:
        NAME="Ubuntu"
        VERSION_ID="25.04"
        PRETTY_NAME="Ubuntu 25.04"

    Returns a dictionary with "name", "version" and "pretty_name".
    Missing values are None.
    """
    for path in os_release_paths:
        content = read_text_file(path)
        if content is None:
            continue
        data = parse_key_value_lines(content, "=")
        return {
            "name": data.get("NAME") or None,
            "version": data.get("VERSION") or data.get("VERSION_ID") or None,
            "pretty_name": data.get("PRETTY_NAME") or None,
        }
    return {"name": None, "version": None, "pretty_name": None}


def get_kernel_version() -> Optional[str]:
    """Return the running kernel release, like the command `uname -r`."""
    release = platform.release()
    return release or None


def get_hostname() -> Optional[str]:
    """Return the computer name, like the command `hostname`."""
    name = socket.gethostname()
    return name or None


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

def get_cpu_model(cpuinfo_path: str = CPUINFO_PATH) -> Optional[str]:
    """Return the CPU model name from /proc/cpuinfo.

    /proc/cpuinfo has one block per logical core. The model name is the
    same in every block, so the first match is enough.
    If the file cannot be read, platform.processor() is used as a backup.
    """
    content = read_text_file(cpuinfo_path)
    if content is not None:
        data = parse_key_value_lines(content, ":")
        for key in _CPU_MODEL_KEYS:
            if data.get(key):
                return data[key]

    fallback = platform.processor()
    return fallback or None


def get_logical_cpu_count() -> Optional[int]:
    """Return the number of logical CPU cores, like `nproc --all`.

    "Logical" cores include Hyper-Threading / SMT threads. A CPU with
    4 physical cores and 2 threads per core shows 8 logical cores.
    os.cpu_count() can return None if Python cannot find the value.
    """
    return os.cpu_count()


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def _meminfo_value_in_bytes(meminfo: Dict[str, str], key: str) -> Optional[int]:
    """Convert a /proc/meminfo value such as "8000000 kB" into bytes."""
    raw_value = meminfo.get(key)
    if not raw_value:
        return None
    try:
        number = int(raw_value.split()[0])
    except (ValueError, IndexError):
        return None
    return number * BYTES_PER_KIB


def calculate_memory_usage(total_bytes: Optional[int], available_bytes: Optional[int]) -> Dict[str, Any]:
    """Calculate used memory and usage percentage.

    Used memory = total - available.
    This is the same idea used by `free`: memory used by the disk cache
    can be given back to programs, so it is counted as available.
    """
    used_bytes: Optional[int] = None
    if total_bytes is not None and available_bytes is not None:
        used_bytes = max(total_bytes - available_bytes, 0)
    return {
        "used_bytes": used_bytes,
        "usage_percent": calculate_percentage(used_bytes, total_bytes),
    }


def get_memory_info(meminfo_path: str = MEMINFO_PATH) -> Dict[str, Any]:
    """Read total and available RAM from /proc/meminfo.

    "MemAvailable" exists on Linux kernels 3.14 and newer. On very old
    kernels it is missing, so we estimate it as MemFree + Buffers + Cached
    and set "available_is_estimate" to True.
    """
    result: Dict[str, Any] = {
        "total_bytes": None,
        "available_bytes": None,
        "used_bytes": None,
        "usage_percent": None,
        "available_is_estimate": False,
    }

    content = read_text_file(meminfo_path)
    if content is None:
        return result

    meminfo = parse_key_value_lines(content, ":")
    total = _meminfo_value_in_bytes(meminfo, "MemTotal")
    available = _meminfo_value_in_bytes(meminfo, "MemAvailable")

    if available is None:
        parts = [_meminfo_value_in_bytes(meminfo, key) for key in ("MemFree", "Buffers", "Cached")]
        if all(part is not None for part in parts):
            available = sum(parts)  # type: ignore[arg-type]
            result["available_is_estimate"] = True

    result["total_bytes"] = total
    result["available_bytes"] = available
    result.update(calculate_memory_usage(total, available))
    return result


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

def calculate_disk_usage(used_bytes: int, free_bytes: int) -> Optional[float]:
    """Calculate disk usage percentage in the same way as `df`.

    Linux filesystems (like ext4) keep about 5% of space reserved for
    root. Normal users cannot use it. `df` therefore calculates:

        usage % = used / (used + available to normal users)

    This is why `df` can show 100% while some space still exists.
    """
    return calculate_percentage(used_bytes, used_bytes + free_bytes)


def get_disk_info(path: str = DEFAULT_DISK_PATH) -> Dict[str, Any]:
    """Return size information for the filesystem that contains `path`.

    shutil.disk_usage() uses the statvfs() system call. It only reads
    information, it does not scan files, so it is fast and safe.

    Raises OSError if the path does not exist or cannot be accessed.
    The caller (collect_system_info) turns that error into a warning.
    """
    usage = shutil.disk_usage(path)
    return {
        "path": path,
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "used_bytes": usage.used,
        "usage_percent": calculate_disk_usage(usage.used, usage.free),
    }


# ---------------------------------------------------------------------------
# Uptime
# ---------------------------------------------------------------------------

def get_uptime_seconds(uptime_path: str = UPTIME_PATH) -> Optional[float]:
    """Return how many seconds the system has been running.

    /proc/uptime contains two numbers, for example "12345.67 98765.43".
    The first number is the uptime in seconds. The second one is the
    total idle time of all cores, which we do not need here.
    """
    content = read_text_file(uptime_path)
    if not content:
        return None
    try:
        return float(content.split()[0])
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

def _safe_collect(label: str, function: Callable[..., Any], default: Any,
                  warnings: List[str], *args: Any) -> Any:
    """Run one collector function and never let it crash the report.

    If the function raises an exception, the error is saved as a warning
    and `default` is returned instead. This way, one broken source (for
    example, a disk path that does not exist) does not hide the other
    information that the technician needs.
    """
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001 - we want to catch everything here
        warnings.append(f"{label}: could not be collected ({type(error).__name__}: {error})")
        return default


def _find_missing_values(info: Dict[str, Any]) -> List[str]:
    """Return warnings for every important value that is None."""
    checks = [
        ("Distribution name", info["os"]["distribution"]),
        ("Kernel version", info["os"]["kernel"]),
        ("Hostname", info["os"]["hostname"]),
        ("CPU model", info["cpu"]["model"]),
        ("Logical CPU cores", info["cpu"]["logical_cores"]),
        ("Total RAM", info["memory"]["total_bytes"]),
        ("Available RAM", info["memory"]["available_bytes"]),
        ("Total disk capacity", info["disk"]["total_bytes"]),
        ("Available disk space", info["disk"]["free_bytes"]),
        ("System uptime", info["uptime"]["seconds"]),
    ]
    return [f"{name}: information not available" for name, value in checks if value is None]


def collect_system_info(disk_path: str = DEFAULT_DISK_PATH) -> Dict[str, Any]:
    """Collect all MODULE 01 information and return it as a dictionary.

    The dictionary uses only simple types (str, int, float, bool, None,
    list, dict), so it can be printed as text or converted to JSON
    without extra work.
    """
    warnings: List[str] = []

    if platform.system() != "Linux":
        warnings.append(
            f"This tool is designed for Linux, but this system is "
            f"'{platform.system() or 'unknown'}'. Some values may be missing."
        )

    empty_distribution = {"name": None, "version": None, "pretty_name": None}
    empty_memory = {"total_bytes": None, "available_bytes": None, "used_bytes": None,
                    "usage_percent": None, "available_is_estimate": False}
    empty_disk = {"path": disk_path, "total_bytes": None, "free_bytes": None,
                  "used_bytes": None, "usage_percent": None}

    distribution = _safe_collect("Distribution", get_distribution_info, empty_distribution, warnings)
    memory = _safe_collect("Memory", get_memory_info, empty_memory, warnings)
    disk = _safe_collect(f"Disk ({disk_path})", get_disk_info, empty_disk, warnings, disk_path)

    info: Dict[str, Any] = {
        "tool": {"name": "linux-diagnostics", "version": __version__, "module": "system_info"},
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "os": {
            "distribution": distribution["name"],
            "version": distribution["version"],
            "pretty_name": distribution["pretty_name"],
            "kernel": _safe_collect("Kernel", get_kernel_version, None, warnings),
            "hostname": _safe_collect("Hostname", get_hostname, None, warnings),
        },
        "cpu": {
            "model": _safe_collect("CPU model", get_cpu_model, None, warnings),
            "logical_cores": _safe_collect("CPU cores", get_logical_cpu_count, None, warnings),
        },
        "memory": memory,
        "disk": disk,
        "uptime": {"seconds": _safe_collect("Uptime", get_uptime_seconds, None, warnings)},
        "warnings": warnings,
    }

    if memory.get("available_is_estimate"):
        warnings.append("Available RAM: estimated (MemAvailable is missing on this kernel)")

    warnings.extend(_find_missing_values(info))
    return info
