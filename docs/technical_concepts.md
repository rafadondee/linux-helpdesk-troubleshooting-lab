# Technical Concepts

This document explains the concepts behind **Module 01 — System Information**.
Each section has: what it is, where Linux stores it, how the tool reads it,
and a practical example.

---

## 1. Linux kernel

**What it is.** The kernel is the core of the operating system. It controls
the hardware (CPU, memory, disks, network) and lets programs use it. When
people say "Linux", strictly they mean the kernel.

**The version.** A kernel version looks like `6.14.0-15-generic`:

| Part | Meaning |
|------|---------|
| `6.14.0` | Upstream kernel version (major.minor.patch) |
| `15` | Ubuntu build number of this kernel |
| `generic` | Kernel flavour (Ubuntu's standard desktop/server build) |

**How the tool reads it.** `platform.release()` → uses the `uname()` system
call, the same as the command `uname -r`.

**Why it matters for support.** Drivers and some software only work with
specific kernel versions. After an update, a problem that "started yesterday"
may be related to a new kernel. Comparing `uname -r` with
`ls /boot/vmlinuz-*` shows if a reboot is pending to load a newer kernel.

---

## 2. Linux distribution

**What it is.** A distribution ("distro") is the kernel **plus** everything
else: package manager, desktop, tools, default settings. Examples: Ubuntu,
Debian, Fedora, Rocky Linux.

**Where Linux stores it.** `/etc/os-release` — a standard text file:

```
PRETTY_NAME="Ubuntu 25.04"
NAME="Ubuntu"
VERSION_ID="25.04"
VERSION="25.04 (Plucky Puffin)"
ID=ubuntu
```

**How the tool reads it.** It reads the file, splits each line at the first
`=`, removes quotes, and keeps `NAME`, `VERSION` (or `VERSION_ID`) and
`PRETTY_NAME`. If `/etc/os-release` does not exist, it tries
`/usr/lib/os-release` (the official fallback location).

**Why it matters for support.** Installation instructions are different on
each distro (`apt` on Ubuntu, `dnf` on Fedora). Version also matters: Ubuntu
25.04 is a short-term release (9 months of support), while LTS versions like
24.04 have 5 years.

---

## 3. Hostname

**What it is.** The name of the computer on the network, for example
`helpdesk-lab-vm`.

**How the tool reads it.** `socket.gethostname()`, same as the command `hostname`.

**Security note.** The hostname can identify a person or a company computer
(`maria-laptop-finance`). That is why the tool has the `--redact` option.

---

## 4. CPU

**What it is.** The Central Processing Unit runs the instructions of all
programs.

**Where Linux stores it.** `/proc/cpuinfo` has one block per logical core:

```
processor   : 0
model name  : Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
...
processor   : 1
model name  : Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
```

**How the tool reads it.** It reads the first `model name` line. ARM
computers (like a Raspberry Pi) do not have `model name`, so the tool also
checks `Model` and `Hardware`. If nothing is found, it uses
`platform.processor()` as a backup.

---

## 5. Logical CPU cores

**Physical vs logical.** A *physical core* is a real processing unit in the
chip. With **Hyper-Threading** (Intel) or **SMT** (AMD), one physical core can
run two threads at the same time, so Linux sees two **logical** cores.

```
1 CPU socket × 4 physical cores × 2 threads per core = 8 logical cores
```

**How the tool reads it.** `os.cpu_count()` — same as `nproc --all`.
The command `lscpu` shows the full breakdown (sockets, cores, threads).

**In VirtualBox** the VM only sees the number of CPUs you assigned in the VM
settings, not the real number of cores in your physical computer.

**Why it matters for support.** A **load average** (command `uptime`) of 4.0
is a problem on a 2-core machine but normal on a 16-core machine. You need the
core count to understand load.

---

## 6. RAM

**What it is.** Random Access Memory is fast, temporary memory. Programs and
their data live in RAM while they run. When the computer turns off, RAM is
cleared.

**Where Linux stores it.** `/proc/meminfo`:

```
MemTotal:        4012608 kB
MemFree:          310452 kB
MemAvailable:    2654208 kB
Buffers:           98304 kB
Cached:          2101248 kB
```

> **Note:** the kernel writes `kB`, but the real unit is **KiB** (1024 bytes).
> The tool multiplies by 1024.

### Units: GB vs GiB

| Unit | Size | Used by |
|------|------|---------|
| GB (gigabyte) | 1000³ bytes = 1,000,000,000 | Disk manufacturers |
| GiB (gibibyte) | 1024³ bytes = 1,073,741,824 | Linux tools (`free -h`, `df -h`), this tool |

This is why a "500 GB" disk shows about "465 GiB" in Linux. Nothing is missing.

---

## 7. Available memory (and why "free" is not the right number)

This is one of the most misunderstood topics in Linux support.

Linux uses **unused RAM as a disk cache** (`Buffers` and `Cached`) to make
the system faster. When a program needs memory, the kernel gives cache
memory back immediately. So:

- `MemFree` = memory that is completely unused. Often **very low**, and that is normal.
- `MemAvailable` = memory that programs can really use (free + reclaimable cache).
  **This is the number that matters.**

The tool calculates:

```
used memory   = MemTotal - MemAvailable
usage percent = used / MemTotal × 100
```

Example with the values above:

```
used  = 4012608 - 2654208 = 1358400 KiB  (about 1.3 GiB)
usage = 1358400 / 4012608 × 100 = 33.9 %
```

**Old kernels.** `MemAvailable` exists since kernel 3.14 (2014). If it is
missing, the tool estimates `MemFree + Buffers + Cached` and shows a warning.

> A user says "Linux is using 95% of my RAM!" after looking at `MemFree`.
> Usually `MemAvailable` shows plenty of memory and there is no problem.

---

## 8. Disk space

**Filesystem and mount point.** A disk partition is formatted with a
**filesystem** (like `ext4`) and attached to a folder called a **mount point**.
`/` is the root filesystem. `/home` may be on the same or a different partition.

**How the tool reads it.** `shutil.disk_usage(path)` uses the `statvfs()`
system call. It asks the kernel for the filesystem size. It does **not** scan
files, so it is instant and safe.

| Value | Meaning |
|-------|---------|
| `total` | Size of the filesystem |
| `used` | Space used by files |
| `free` | Space available to **normal users** |

### Reserved blocks: why `used + free ≠ total`

`ext4` reserves about **5%** of the space for the `root` user. This lets the
system keep working (logs, root login) when users fill the disk. Normal users
cannot use these blocks.

So the tool uses the same formula as `df`:

```
usage % = used / (used + free) × 100
```

Example: total 100 GiB, used 50 GiB, free 45 GiB (5 GiB reserved)
→ usage = 50 / 95 = **52.6 %**, not 50 %.

This means "100%" in `df` really means "users cannot write any more".

---

## 9. System uptime

**What it is.** How long the system has been running since the last boot.

**Where Linux stores it.** `/proc/uptime`:

```
11722.35 43810.12
```

- First number: seconds since boot (used by the tool).
- Second number: total idle time of all cores, in seconds.

The tool converts seconds into text: `11722` seconds → `3 hours, 15 minutes`.

**Why it matters for support.**
- "Did you restart the computer?" — uptime gives the true answer.
- Very long uptime (months) may mean security updates for the kernel are
  installed but **not active** (a reboot is needed).
- Very short uptime on a server may mean an unexpected reboot or crash.

---

## 10. The `/proc` filesystem

`/proc` is a **virtual filesystem**. Its files are not on the disk: the kernel
creates their content at the moment you read them. That is why the values
are always current, and why reading them is safe and fast.

```bash
ls /proc            # numbers are process IDs, files are system information
cat /proc/uptime    # changes every time you run it
```

---

## 11. Python modules and functions used

| Module / function | What it does in this project |
|-------------------|------------------------------|
| `argparse` | Creates the CLI: options, `--help` text, error for unknown options (exit code 2) |
| `json.dumps()` | Converts the Python dictionary into JSON text (`None` → `null`, `False` → `false`) |
| `platform.release()` | Kernel release (`uname -r`) |
| `platform.system()` | OS name (`Linux`, `Windows`, `Darwin`) — used to warn on non-Linux systems |
| `platform.processor()` | CPU fallback when `/proc/cpuinfo` is not available |
| `socket.gethostname()` | Computer name |
| `os.cpu_count()` | Number of logical cores |
| `shutil.disk_usage()` | Disk total/used/free through `statvfs()` |
| `open(path, "r")` | Reads text files in **read-only** mode |
| `datetime.now(timezone.utc)` | Report timestamp in UTC (same time zone everywhere) |
| `unittest` | Test framework included with Python |
| `unittest.mock` | Replaces real functions with fake ones during tests |
| `tempfile` | Creates temporary fake system files during tests |

### Key Python ideas in the code

**Functions with default parameters**

```python
def get_memory_info(meminfo_path: str = MEMINFO_PATH) -> dict:
```

In real use, the default `/proc/meminfo` is used. In tests, we pass a
temporary fake file. This is a simple form of *dependency injection*.

**Type hints**

```python
def calculate_percentage(part: Optional[float], total: Optional[float]) -> Optional[float]:
```

They do not change how the code runs. They document what the function
expects and returns. `Optional[float]` means "a float or `None`".

**`try` / `except`**

```python
try:
    return float(content.split()[0])
except (ValueError, IndexError):
    return None
```

Catch only the errors you expect, as close as possible to where they happen.
The wide `except Exception` is used only in two "safety net" places
(`_safe_collect` and `main`), on purpose.

**Mocks in tests**

```python
@mock.patch("linux_diagnostics.system_info.shutil.disk_usage")
def test_disk_values(self, mock_disk_usage):
    mock_disk_usage.return_value = DiskUsage(total=100, used=40, free=60)
```

During this test, `shutil.disk_usage` is replaced by a fake that returns
our values. The test does not depend on the real disk, so it gives the same
result on every computer.

---

## 12. Operating system information: summary table

| Item | Linux source | Command to compare | Can fail when... |
|------|--------------|--------------------|------------------|
| Distribution | `/etc/os-release` | `cat /etc/os-release` | Very old or minimal system without the file |
| Kernel | `uname()` | `uname -r` | Almost never |
| Hostname | `gethostname()` | `hostname` | Almost never |
| CPU model | `/proc/cpuinfo` | `lscpu` | Some ARM/virtual CPUs do not report a name |
| Logical cores | `sched/sysconf` | `nproc --all` | Rare; returns `None` |
| RAM | `/proc/meminfo` | `free -h` | `/proc` not mounted (some containers) |
| Disk | `statvfs()` | `df -h /` | Path does not exist or no permission |
| Uptime | `/proc/uptime` | `uptime -p` | `/proc` not mounted |
