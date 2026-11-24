# Linux Help Desk Troubleshooting Lab

![tests](https://img.shields.io/badge/tests-67%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-lightgrey)
![license](https://img.shields.io/badge/license-MIT-green)

A **read-only Linux diagnostic toolkit** for Help Desk and IT support work.
It collects the information a support technician usually asks for first:
*Which Linux is this? How much memory is free? Is the disk full? When was
the last reboot?* — and shows it in one clear report or as JSON.

The project is also a **learning lab**: every part of the code is
documented, and the `docs/` folder explains the Linux and Python concepts
behind it.

---

## Table of contents

- [Main objectives](#main-objectives)
- [Features](#features)
- [Technologies used](#technologies-used)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Command-line options](#command-line-options)
- [Example output](#example-output)
- [Testing](#testing)
- [Safety and security](#safety-and-security)
- [Current limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [License](#license)

---

## Main objectives

1. Give IT support technicians a **fast, safe first look** at a Linux system.
2. Practise real **Linux administration** concepts: `/proc`, `/etc/os-release`,
   kernel, memory, filesystems.
3. Practise **professional Python**: modules, CLI, error handling, JSON,
   automated tests with mocks.
4. Build a base that can grow into a complete troubleshooting toolkit
   (network, disks, services, permissions, incident reports).

## Features

**Module 01 — System Information** (version 0.1.0) collects:

| # | Information | Source on Linux | Equivalent command |
|---|-------------|-----------------|--------------------|
| 1 | Distribution and version | `/etc/os-release` | `cat /etc/os-release` |
| 2 | Kernel version | `uname()` system call | `uname -r` |
| 3 | Hostname | `gethostname()` | `hostname` |
| 4 | CPU model | `/proc/cpuinfo` | `lscpu` |
| 5 | Logical CPU cores | `os.cpu_count()` | `nproc --all` |
| 6 | Total RAM | `/proc/meminfo` → `MemTotal` | `free -h` |
| 7 | Available RAM | `/proc/meminfo` → `MemAvailable` | `free -h` |
| 8 | Memory usage % | calculated | `free -h` |
| 9 | Total disk capacity | `statvfs()` system call | `df -h /` |
| 10 | Available disk space | `statvfs()` system call | `df -h /` |
| 11 | Disk usage % | calculated (same formula as `df`) | `df -h /` |
| 12 | System uptime | `/proc/uptime` | `uptime -p` |

Other properties:

- **Read-only** — it only opens files for reading. It never changes settings or deletes files.
- **No root needed** — works as a normal user, no `sudo`.
- **No external dependencies** — only the Python standard library.
- **Graceful errors** — if one value cannot be read, it shows `Unavailable`
  and a warning, and the rest of the report still works.
- **Text or JSON output** — readable for people, machine-readable for scripts.
- **`--redact` option** — hides the hostname before you share a report.
- **Extensible** — new diagnostic modules can be added without rewriting the CLI.

## Technologies used

| Technology | Why |
|------------|-----|
| Python 3 (standard library only) | Installed by default on Ubuntu; no `pip install` needed |
| `argparse` | Professional command-line interface with automatic `--help` |
| `json` | Machine-readable output |
| `platform`, `socket`, `os`, `shutil` | Read operating system information safely |
| `unittest` + `unittest.mock` | Automated tests that do not depend on the real computer |
| Linux `/proc` filesystem | Live kernel information (memory, CPU, uptime) |
| Git + GitHub Actions | Version control and automatic tests on every push |

## Project structure

```
linux-helpdesk-troubleshooting-lab/
├── src/
│   └── linux_diagnostics/
│       ├── __init__.py        # package version
│       ├── __main__.py        # allows "python3 -m linux_diagnostics"
│       ├── main.py            # command-line interface and text report
│       ├── system_info.py     # MODULE 01: collects system information
│       └── utils.py           # shared helpers (read files, format bytes...)
├── tests/
│   ├── __init__.py            # adds "src" to the import path
│   ├── test_system_info.py    # tests for MODULE 01
│   ├── test_main.py           # tests for the CLI, JSON and errors
│   └── test_utils.py          # tests for the helpers
├── docs/
│   ├── project_architecture.md
│   ├── technical_concepts.md
│   └── learning_guide.md
├── examples/
│   ├── README.md
│   ├── sample_output.txt      # fake example of the text report
│   ├── sample_output.json     # fake example of the JSON report
│   └── save_report.sh         # saves a dated JSON report
├── .github/workflows/tests.yml  # runs the tests on GitHub
├── .gitignore
├── LICENSE
├── pyproject.toml             # optional: install as a command
├── README.md
└── requirements.txt           # empty: no external packages
```

Changes from the original plan are explained in
[docs/project_architecture.md](docs/project_architecture.md#changes-from-the-original-plan).

## Installation

Requirements: a Linux system with **Python 3.8 or newer** (Ubuntu 25.04 has
Python 3.13). Check with:

```bash
python3 --version
```

### Option A — run without installing (recommended for learning)

```bash
git clone https://github.com/<your-username>/linux-helpdesk-troubleshooting-lab.git
cd linux-helpdesk-troubleshooting-lab
PYTHONPATH=src python3 -m linux_diagnostics
```

`PYTHONPATH=src` tells Python where to find the package for this one command.
Nothing is installed on the system.

### Option B — install as a command in a virtual environment

Ubuntu protects the system Python (PEP 668), so install inside a
virtual environment:

```bash
python3 -m venv .venv          # on Ubuntu you may need the package python3-venv
source .venv/bin/activate
pip install .
linux-diagnostics --help
deactivate                     # leave the virtual environment
```

## Usage

The examples below use Option A. If you used Option B, replace
`PYTHONPATH=src python3 -m linux_diagnostics` with `linux-diagnostics`.

```bash
# Full readable report
PYTHONPATH=src python3 -m linux_diagnostics

# JSON output
PYTHONPATH=src python3 -m linux_diagnostics --json

# Check the disk that contains /home instead of /
PYTHONPATH=src python3 -m linux_diagnostics --disk-path /home

# Hide the hostname before sharing the report in a ticket
PYTHONPATH=src python3 -m linux_diagnostics --redact

# Save a JSON report to a file
PYTHONPATH=src python3 -m linux_diagnostics --json --redact > report.json

# Or use the helper script (saves to reports/ with a date in the name)
bash examples/save_report.sh
```

## Command-line options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help and exit |
| `--version` | Show the program version and exit |
| `--json` | Print the result as valid JSON |
| `--module {system}` | Diagnostic module to run (default: `system`; more modules in the future) |
| `--disk-path PATH` | Filesystem path to check for disk space (default: `/`) |
| `--redact` | Replace the hostname with `[REDACTED]` |

**Exit codes**

| Code | Meaning |
|------|---------|
| `0` | Report created (it may still contain warnings for missing values) |
| `1` | Unexpected error — no report was created |
| `2` | Invalid command-line option |
| `130` | Stopped by the user with `Ctrl+C` |

## Example output

The values below are **fake** example data
(see [examples/](examples/)).

```
================================================
Linux Help Desk Diagnostics - System Information
================================================
Collected at (UTC) : 2026-01-15T14:30:00+00:00
Tool version       : 0.1.0

[Operating System]
  Distribution     : Ubuntu
  Version          : 25.04 (Plucky Puffin)
  Kernel           : 6.14.0-15-generic
  Hostname         : helpdesk-lab-vm

[CPU]
  Model            : Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
  Logical cores    : 4

[Memory (RAM)]
  Total            : 3.8 GiB
  Available        : 2.5 GiB
  Used             : 1.3 GiB
  Usage            : 33.9%

[Disk (/)]
  Total            : 25.0 GiB
  Available        : 13.1 GiB
  Used             : 10.6 GiB
  Usage            : 44.5%

[Uptime]
  Running for      : 3 hours, 15 minutes
```

When something cannot be read, the report continues and explains why:

```
[Disk (/does/not/exist)]
  Total            : Unavailable
  ...

[Warnings]
  - Disk (/does/not/exist): could not be collected (FileNotFoundError: ...)
  - Total disk capacity: information not available
```

JSON output (shortened — full file in
[examples/sample_output.json](examples/sample_output.json)):

```json
{
  "tool": { "name": "linux-diagnostics", "version": "0.1.0", "module": "system_info" },
  "collected_at": "2026-01-15T14:30:00+00:00",
  "os": { "distribution": "Ubuntu", "version": "25.04 (Plucky Puffin)", "kernel": "6.14.0-15-generic", "hostname": "helpdesk-lab-vm" },
  "memory": { "total_bytes": 4108910592, "available_bytes": 2717908992, "usage_percent": 33.9 },
  "disk": { "path": "/", "total_bytes": 26834087936, "free_bytes": 14118739968, "usage_percent": 44.5 },
  "uptime": { "seconds": 11722.35 },
  "warnings": []
}
```

In JSON, sizes are always in **bytes** and missing values are `null`.

## Testing

The tests use Python's built-in `unittest`. They use temporary fake files
and `unittest.mock`, so they **do not depend on your computer** and they
never read your real system data.

```bash
# Run from the project root folder
python3 -m unittest discover -v
```

**Current result (version 0.1.0):** 67 tests, all passing.

| Environment | Python | Result |
|-------------|--------|--------|
| Ubuntu 22.04 (WSL2, Linux kernel 6.x) | 3.10.12 | 67 passed |
| Windows 11 (development machine) | 3.11.2 | 67 passed |
| GitHub Actions `ubuntu-latest` | 3.10 / 3.12 / 3.13 | runs on every push |

What is tested:

- Reading `/etc/os-release`, `/proc/cpuinfo` (x86 and ARM), `/proc/meminfo`, `/proc/uptime`
- Memory calculations, including old kernels without `MemAvailable`
- Disk calculations, including the reserved-blocks formula used by `df`
- Missing files, empty files and invalid numbers
- Errors inside one collector (the report must continue)
- Text report, JSON validity, `null` values, `--redact`, `--version`, `--help`
- Exit codes for errors, invalid options and `Ctrl+C`

## Safety and security

- The tool only **reads**. Files are opened with mode `"r"`; there is no code
  that writes, deletes or changes system files.
- It does **not** use `sudo` and does **not** run shell commands
  (no `subprocess`), so there is no risk of command injection.
- Reports can contain the **hostname**, which identifies a computer.
  Use `--redact` before sharing. The `reports/` folder is in `.gitignore`.
- The example files in this repository contain only fake data.

## Current limitations

- Only **Module 01 (system information)** exists in version 0.1.0.
- Designed for **Linux**. On Windows or macOS it runs, but most values show
  `Unavailable` (with a warning).
- Reports **one disk path** at a time (default `/`), not all mounted filesystems.
- Shows **logical** CPU cores only, not physical cores or sockets.
- In **containers** (Docker, LXC), memory and CPU values may show the host
  machine, not the container limits.
- Does not save history or compare reports over time.

## Roadmap

The architecture allows each module to be added as a new file plus one line
in the module registry (see
[docs/project_architecture.md](docs/project_architecture.md#how-to-add-a-new-diagnostic-module)).

| Module | Status | Planned content |
|--------|--------|-----------------|
| 01 — System Information | ✅ Done (v0.1.0) | OS, kernel, hostname, CPU, RAM, disk, uptime |
| 02 — Network Diagnostics | 🔜 Next | IP configuration, network interfaces, DNS resolution, connectivity tests |
| 03 — Disk Diagnostics | Planned | All mounted filesystems, inode usage, filesystem types, storage troubleshooting |
| 04 — Service Diagnostics | Planned | Running processes, top CPU/memory processes, systemd service status |
| 05 — Permissions Diagnostics | Planned | File permissions, ownership, users and groups |
| 06 — Incident Reports | Planned | Troubleshooting records, incident documentation, combined diagnostic reports |

Other ideas: configurable warning thresholds (for example "disk above 90%"),
a `--all` option to run every module, and Markdown report export.

## Documentation

| Document | Content |
|----------|---------|
| [docs/project_architecture.md](docs/project_architecture.md) | Why the project is organized this way and how to add modules |
| [docs/technical_concepts.md](docs/technical_concepts.md) | Kernel, distribution, CPU, RAM, disk, uptime and the Python modules used |
| [docs/learning_guide.md](docs/learning_guide.md) | Linux commands, exercises, common mistakes and troubleshooting scenarios |

## License

[MIT](LICENSE)
