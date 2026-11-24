"""Command-line interface (CLI) for the Linux diagnostic toolkit.

This file is the "front door" of the program. It:
1. reads the command-line options (argparse);
2. calls the selected diagnostic module to collect data;
3. prints the result as readable text or as JSON;
4. returns an exit code (0 = success, 1 = error).

The diagnostic modules never print anything. They only return data.
This separation makes the modules easy to test and easy to reuse.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import __version__
from .system_info import DEFAULT_DISK_PATH, collect_system_info
from .utils import display_value, format_bytes, format_duration, format_percentage

# Exit codes. Scripts and monitoring tools read these numbers.
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130  # standard code for "stopped with Ctrl+C"

REDACTED = "[REDACTED]"


# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------
# Each diagnostic module has two parts:
#   "collect": a function that receives the parsed options and returns a dict;
#   "render":  a function that receives that dict and returns readable text.
# To add a new module (for example "network"), write the two functions and
# add one entry here. Nothing else in this file needs to change.

def _collect_system(options: argparse.Namespace) -> Dict[str, Any]:
    return collect_system_info(disk_path=options.disk_path)


def render_system_report(info: Dict[str, Any]) -> str:
    """Build the human-readable text report for MODULE 01."""
    os_info = info["os"]
    cpu = info["cpu"]
    memory = info["memory"]
    disk = info["disk"]

    title = "Linux Help Desk Diagnostics - System Information"
    line = "=" * len(title)

    memory_used = format_bytes(memory["used_bytes"])
    disk_used = format_bytes(disk["used_bytes"])

    rows: List[str] = [
        line,
        title,
        line,
        f"Collected at (UTC) : {info['collected_at']}",
        f"Tool version       : {info['tool']['version']}",
        "",
        "[Operating System]",
        f"  Distribution     : {display_value(os_info['distribution'])}",
        f"  Version          : {display_value(os_info['version'])}",
        f"  Kernel           : {display_value(os_info['kernel'])}",
        f"  Hostname         : {display_value(os_info['hostname'])}",
        "",
        "[CPU]",
        f"  Model            : {display_value(cpu['model'])}",
        f"  Logical cores    : {display_value(cpu['logical_cores'])}",
        "",
        "[Memory (RAM)]",
        f"  Total            : {format_bytes(memory['total_bytes'])}",
        f"  Available        : {format_bytes(memory['available_bytes'])}",
        f"  Used             : {memory_used}",
        f"  Usage            : {format_percentage(memory['usage_percent'])}",
        "",
        f"[Disk ({disk['path']})]",
        f"  Total            : {format_bytes(disk['total_bytes'])}",
        f"  Available        : {format_bytes(disk['free_bytes'])}",
        f"  Used             : {disk_used}",
        f"  Usage            : {format_percentage(disk['usage_percent'])}",
        "",
        "[Uptime]",
        f"  Running for      : {format_duration(info['uptime']['seconds'])}",
    ]

    if info.get("warnings"):
        rows.append("")
        rows.append("[Warnings]")
        rows.extend(f"  - {warning}" for warning in info["warnings"])

    return "\n".join(rows)


DIAGNOSTIC_MODULES: Dict[str, Dict[str, Callable[..., Any]]] = {
    "system": {"collect": _collect_system, "render": render_system_report},
}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def redact_sensitive_data(info: Dict[str, Any]) -> Dict[str, Any]:
    """Hide values that identify a specific computer (the hostname).

    Use --redact before you paste a report into a public ticket, forum
    or GitHub issue. The original dictionary is not changed.
    """
    redacted = json.loads(json.dumps(info))  # simple deep copy
    if "os" in redacted and redacted["os"].get("hostname") is not None:
        redacted["os"]["hostname"] = REDACTED
    return redacted


def render_json_report(info: Dict[str, Any]) -> str:
    """Return the collected data as formatted, valid JSON text."""
    return json.dumps(info, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all command-line options."""
    parser = argparse.ArgumentParser(
        prog="linux-diagnostics",
        description=(
            "Read-only Linux diagnostic toolkit for Help Desk and IT support. "
            "Collects system information without root privileges and without "
            "changing anything on the computer."
        ),
        epilog=(
            "Examples:\n"
            "  linux-diagnostics\n"
            "  linux-diagnostics --json\n"
            "  linux-diagnostics --disk-path /home --redact\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show the program version and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as machine-readable JSON",
    )
    parser.add_argument(
        "--module",
        choices=sorted(DIAGNOSTIC_MODULES),
        default="system",
        help="diagnostic module to run (default: system)",
    )
    parser.add_argument(
        "--disk-path",
        default=DEFAULT_DISK_PATH,
        metavar="PATH",
        help=f"filesystem path to check for disk space (default: {DEFAULT_DISK_PATH})",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="hide the hostname, useful before sharing a report",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point. Returns the exit code."""
    parser = build_parser()
    options = parser.parse_args(argv)
    module = DIAGNOSTIC_MODULES[options.module]

    try:
        info = module["collect"](options)
        if options.redact:
            info = redact_sensitive_data(info)

        if options.json:
            output = render_json_report(info)
        else:
            output = module["render"](info)
        print(output)
        return EXIT_SUCCESS

    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return EXIT_INTERRUPTED
    except Exception as error:  # noqa: BLE001 - last safety net for the user
        message = f"{type(error).__name__}: {error}"
        if options.json:
            print(json.dumps({"error": message}), file=sys.stderr)
        else:
            print(f"Error: unexpected problem while collecting data - {message}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
