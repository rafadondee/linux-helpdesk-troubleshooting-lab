# Project Architecture

This document explains **how the project is organized** and **why**.
Read it before you change the code or add a new module.

## 1. The big idea: collect, then present

The program has two separate jobs:

1. **Collect** information from the system (files in `/proc`, system calls).
2. **Present** the information to a person (text) or to a program (JSON).

These jobs live in different files:

```
            ┌──────────────────────────┐
  user ───▶ │ main.py  (CLI)           │  reads options (--json, --disk-path ...)
            │                          │
            │  1. calls a module  ─────┼──▶ system_info.py  collect_system_info()
            │                          │        │
            │                          │        ├─▶ reads /etc/os-release, /proc/...
            │                          │        └─▶ uses utils.py helpers
            │  2. receives a dict ◀────┼────────┘
            │  3. text or JSON         │
            └──────────┬───────────────┘
                       ▼
                  terminal output + exit code
```

**Why separate them?**

- `system_info.py` never prints. It only **returns a dictionary**. This makes
  it easy to test: a test calls the function and checks the dictionary.
- The same dictionary can become text, JSON, or (in the future) Markdown or
  HTML, without changing the collection code.
- If one day we build a web dashboard, it can import `system_info.py` directly.

This principle is called **separation of concerns**.

## 2. What each directory does

| Path | Purpose |
|------|---------|
| `src/linux_diagnostics/` | The Python package — the real program |
| `tests/` | Automated tests (`unittest`) |
| `docs/` | Learning and technical documentation |
| `examples/` | Example outputs (fake data) and a helper script |
| `.github/workflows/` | GitHub Actions: runs the tests automatically on every push |

### Why the `src/` folder? ("src layout")

The package is inside `src/` instead of the root folder. This is a common
professional practice because:

- It prevents tests from accidentally importing files that are not part
  of the package.
- It keeps the root folder clean (docs, config, tests are separate from code).

The cost: Python does not find the package automatically. That is why we use
`PYTHONPATH=src` to run it, and why `tests/__init__.py` adds `src` to the
import path.

## 3. The Python modules

| File | Responsibility | Knows about... |
|------|----------------|----------------|
| `__init__.py` | Marks the folder as a package; stores `__version__` | nothing else |
| `__main__.py` | Makes `python3 -m linux_diagnostics` work | `main.py` |
| `main.py` | CLI options, module registry, text/JSON output, exit codes | modules + utils |
| `system_info.py` | MODULE 01: collects the 12 system values | utils |
| `utils.py` | Generic helpers: read a file, parse `KEY=value`, format bytes and time, percentages | nothing else |

Dependencies only go **one way**: `main → system_info → utils`.
`utils.py` never imports the other files. This avoids "circular imports" and
makes each layer easy to understand alone.

### How `system_info.py` is built

Each value has **its own small function**:

```
get_distribution_info()   get_kernel_version()   get_hostname()
get_cpu_model()           get_logical_cpu_count()
get_memory_info()         get_disk_info()        get_uptime_seconds()
```

Then `collect_system_info()` calls all of them. Each call goes through
`_safe_collect()`, which catches any exception and turns it into a **warning**.
So if, for example, the disk path does not exist, you still get the CPU,
memory and uptime information.

Small functions are also easy to test one by one, and file paths are
parameters (for example `get_memory_info(meminfo_path=...)`), so tests can
give a fake file instead of the real `/proc/meminfo`.

### Missing values: `None`

When a value cannot be found, the function returns `None` (not `0`, not an
empty string). This is important: "0 bytes of RAM" is a wrong fact, but
`None` means "we don't know". In the text report `None` becomes `Unavailable`;
in JSON it becomes `null`.

### Error handling in layers

| Layer | What it catches | Result |
|-------|-----------------|--------|
| `read_text_file()` | `OSError` (file missing, no permission) | returns `None` |
| Parsing (`int()`, `float()`) | `ValueError`, `IndexError` | value becomes `None` |
| `_safe_collect()` | any `Exception` inside one collector | warning + default value |
| `main()` | any `Exception` not caught before; `KeyboardInterrupt` | message on stderr, exit code 1 or 130 |

## 4. How to add a new diagnostic module

Example: **MODULE 02 — Network Diagnostics**.

**Step 1.** Create `src/linux_diagnostics/network_info.py` with small,
read-only collector functions and one main function:

```python
def collect_network_info() -> dict:
    """Collect network information and return a dictionary."""
    warnings = []
    return {
        "tool": {...},
        "interfaces": ...,
        "dns_servers": ...,
        "warnings": warnings,
    }
```

Follow the same rules as Module 01: no printing, return `None` for missing
values, use `_safe_collect`-style error handling, reuse `utils.py`.

**Step 2.** In `main.py`, write a render function and add **one entry** to
the registry:

```python
def render_network_report(info): ...

DIAGNOSTIC_MODULES = {
    "system":  {"collect": _collect_system,  "render": render_system_report},
    "network": {"collect": _collect_network, "render": render_network_report},
}
```

The `--module` option reads its choices from this dictionary, so
`--module network` works automatically. `--json` and `--redact` also work
without changes.

**Step 3.** Create `tests/test_network_info.py`. Use fake files and mocks —
never real network calls in unit tests.

**Step 4.** Update the README (features, roadmap) and the docs.

> If a shared helper becomes useful for many modules (for example
> `_safe_collect`), move it to `utils.py` at that moment. Do not move code
> "just in case" before it is needed.

## 5. Changes from the original plan

The original plan proposed a smaller structure. These changes were made:

| Change | Reason |
|--------|--------|
| Added `__main__.py` | Allows the standard command `python3 -m linux_diagnostics` |
| Added `tests/test_main.py` and `tests/test_utils.py` | Keeps each test file focused on one source file |
| Added `pyproject.toml` | Optional installation as the `linux-diagnostics` command; standard modern Python packaging |
| Added `--module`, `--disk-path`, `--redact` options | `--module` prepares for future modules; `--disk-path` is a real help desk need (`/home` full); `--redact` supports safe report sharing (information security) |
| Added `.github/workflows/tests.yml` | Shows tests passing on GitHub; professional practice (CI) |
| Added `examples/save_report.sh` | Shows how other tools can use the JSON output |
| `requirements.txt` is empty | Only the standard library is used; the file documents that fact |
