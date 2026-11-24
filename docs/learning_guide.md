# Learning Guide

This guide helps you **practise** the skills behind this project in your own
Ubuntu VM. All commands here are **read-only** and run **without `sudo`**,
unless clearly marked.

Work in this order:

1. [Linux commands](#1-linux-commands-used-in-the-project)
2. [Practical exercises](#2-practical-exercises)
3. [Common mistakes](#3-common-mistakes)
4. [Troubleshooting scenarios](#4-troubleshooting-scenarios)
5. [Interview questions](#5-interview-questions-you-should-be-able-to-answer)

---

## 1. Linux commands used in the project

Each piece of information in the tool has a Linux command that shows the
same thing. A good technician knows **both**: the command (works on any
computer) and the tool (fast, consistent report).

| Command | What it does | Why it is useful for IT support |
|---------|--------------|---------------------------------|
| `cat /etc/os-release` | Shows distribution name and version | First question in any ticket: "Which Linux and which version?" |
| `lsb_release -a` | Same information, different format (may not be installed) | Common in older guides |
| `uname -r` | Kernel release | Driver problems, pending reboot after update |
| `uname -a` | All kernel information (name, host, version, architecture) | Quick overview |
| `hostname` | Computer name | Confirm you are on the right machine (very important with SSH!) |
| `lscpu` | CPU details: model, sockets, cores, threads | Performance problems, VM configuration |
| `nproc --all` | Number of logical cores | Understand load average |
| `cat /proc/cpuinfo` | Raw CPU information from the kernel | What the tool reads |
| `free -h` | Memory usage in human units | "The computer is slow" |
| `cat /proc/meminfo` | Raw memory information | What the tool reads |
| `df -h` | Disk usage of all filesystems | "I cannot save files", "update failed" |
| `df -h /home` | Disk usage of the filesystem that contains `/home` | Same as `--disk-path /home` |
| `df -i` | **Inode** usage (number of files) | Disk "full" even with free GiB |
| `du -sh ~/*` | Size of each item in your home folder | Find what fills the disk |
| `uptime` | Uptime, logged users, load average | Was it restarted? Is it overloaded? |
| `uptime -p` | Uptime in "pretty" format | Easy to read |
| `cat /proc/uptime` | Raw uptime in seconds | What the tool reads |
| `who -b` | Date and time of last boot | Exact reboot time |

### Commands for this project (Python and Git)

| Command | What it does |
|---------|--------------|
| `python3 --version` | Show Python version |
| `PYTHONPATH=src python3 -m linux_diagnostics` | Run the tool without installing |
| `python3 -m unittest discover -v` | Run all tests, one line per test |
| `python3 -m json.tool file.json` | Validate and pretty-print JSON |
| `echo $?` | Show the exit code of the last command |
| `git status` / `git log --oneline` | See changes / history |

---

## 2. Practical exercises

Do these in your Ubuntu VM. Write your answers in a notebook — they are
excellent interview material.

### Exercise 1 — Compare the tool with Linux commands

```bash
PYTHONPATH=src python3 -m linux_diagnostics
cat /etc/os-release
uname -r
nproc --all
free -h
df -h /
uptime -p
```

**Questions:**
- Do the values match? Note any small differences and explain them
  (hint: rounding, `free -h` uses `Gi`, timing).
- Why can `free` show low "free" memory but high "available" memory?

### Exercise 2 — Calculate memory usage by hand

```bash
grep -E 'MemTotal|MemAvailable' /proc/meminfo
```

Calculate `(MemTotal - MemAvailable) / MemTotal × 100` with a calculator.
Compare with the tool's "Usage" value.

### Exercise 3 — Disk usage and reserved blocks

```bash
df -B1 /
```

Using the numbers (`Used` and `Available`), calculate
`Used / (Used + Available) × 100`. Then calculate `Used / Size × 100`.
Which one matches `df`'s `Use%`? Why? (See `technical_concepts.md`, section 8.)

### Exercise 4 — See uptime change

```bash
cat /proc/uptime; sleep 5; cat /proc/uptime
```

How much did the first number change? Now restart the VM and run the tool
again. What happened to "Running for"?

### Exercise 5 — Use JSON output

```bash
PYTHONPATH=src python3 -m linux_diagnostics --json > /tmp/report.json
python3 -m json.tool /tmp/report.json > /dev/null && echo "valid JSON"
python3 -c "import json; d=json.load(open('/tmp/report.json')); print(d['disk']['usage_percent'])"
```

**Challenge:** write a small Bash script that prints `WARNING` if disk usage
is above 80%.

### Exercise 6 — Test error handling

```bash
PYTHONPATH=src python3 -m linux_diagnostics --disk-path /path/that/does/not/exist
echo "exit code: $?"
PYTHONPATH=src python3 -m linux_diagnostics --wrong-option
echo "exit code: $?"
```

Why is the first exit code `0` but the second `2`? (Look at the "Exit codes"
table in the README.)

### Exercise 7 — Break a test on purpose

1. Open `src/linux_diagnostics/utils.py`.
2. In `calculate_percentage`, change `* 100` to `* 10`.
3. Run `python3 -m unittest discover -v`.
4. Read which tests fail and **why**. Then undo the change and run the tests again.

This teaches you how tests protect the code.

### Exercise 8 — Change the VM and observe

Shut down the VM. In VirtualBox, change the number of CPUs or the RAM.
Start it again and run the tool. Did "Logical cores" and "Total RAM" change?

### Exercise 9 — Redact before sharing

Run the tool with and without `--redact`. What changes? What other
information in the report could be sensitive in a real company? (Think
about kernel versions and attackers.)

---

## 3. Common mistakes

| Mistake | Why it is wrong | Correct approach |
|---------|-----------------|------------------|
| Looking at `MemFree` to decide if RAM is full | Linux uses free RAM as cache; `MemFree` is always low | Look at `MemAvailable` / "available" column |
| Confusing GB and GiB | 500 GB = ~465 GiB; nothing is missing | Know the unit each tool uses |
| Thinking `df` and `du` must show the same number | `df` asks the filesystem; `du` adds file sizes. Deleted files still open by a process use space in `df` but not in `du` | Use both; check `lsof +L1` (advanced) |
| Running the tool with `sudo` "just in case" | Not needed; running as root without reason is a security risk | Use the least privilege necessary |
| Forgetting `PYTHONPATH=src` | Python cannot find the package: `No module named linux_diagnostics` | Run from the project root with `PYTHONPATH=src` |
| Running tests from inside the `tests/` folder | Imports break | Run `python3 -m unittest discover -v` from the project root |
| Using `pip install` on the system Python in Ubuntu | Ubuntu blocks it (`externally-managed-environment`) | Use a virtual environment (`python3 -m venv .venv`) |
| Posting full reports in public forums | Hostname and versions help attackers | Use `--redact` and review before sharing |
| Thinking disk usage 100% means zero bytes left | Reserved blocks still exist for root | Free space for users is the important value |

---

## 4. Troubleshooting scenarios

Practise these as if you were the Help Desk technician. For each one: what
do you check first, which command, and what do you tell the user?

### Scenario A — "The computer is very slow"

1. Run the tool. Look at **Memory usage** and **Logical cores**.
2. If memory usage is above ~90%: which program uses the memory?
   `top` (press `M` to sort by memory) or `ps aux --sort=-%mem | head`.
3. Check load: `uptime`. Compare the load average with the number of cores.
4. Check **uptime**: a system running for months may need a reboot.

### Scenario B — "I cannot save my files" / "Update failed: no space left on device"

1. Run the tool. Look at **Disk usage**. Also run
   `--disk-path /home` and `--disk-path /var` (logs live in `/var/log`).
2. Use `df -h` to see all filesystems.
3. If disk has free GiB but still "no space": check inodes with `df -i`.
4. Find large folders: `du -sh ~/* | sort -h`.
5. Do **not** delete files without understanding them (especially in `/var`).
   Escalate if system folders are full.

### Scenario C — "It worked yesterday, today it does not"

1. Run the tool. Note the **kernel version** and **uptime**.
2. Did the system reboot recently (short uptime)? Maybe a new kernel loaded.
3. Check recent updates: `grep " install \| upgrade " /var/log/dpkg.log | tail`
   (read-only).
4. Compare `uname -r` with the newest file in `/boot/vmlinuz-*`.

### Scenario D — "Which machine am I connected to?"

You are connected by SSH to many servers. Before **any** change, run
`hostname` (or the tool). Many real incidents happen because someone ran a
command on the wrong server.

### Scenario E — The tool shows "Unavailable"

1. Read the **[Warnings]** section — it says what failed.
2. Is this really Linux? (`uname -s`)
3. Is it a container with a limited `/proc`? (`ls /proc/meminfo`)
4. Run the equivalent command (table in section 1) to compare.

### Scenario F — The user asks you to "just give me the report"

1. Use `--redact`.
2. Use `--json` if another team will process it automatically.
3. Attach the file to the ticket, not to a public chat.

---

## 5. Interview questions you should be able to answer

1. What is the difference between the Linux **kernel** and a **distribution**?
2. How do you find the distribution and kernel version from the terminal?
3. What is the difference between **free** and **available** memory in Linux?
4. What is the difference between a **physical** and a **logical** CPU core?
5. What is `/proc`? Is it stored on the disk?
6. Why can `df` show 100% when there is still space on the disk?
7. What is an **inode**, and how can a disk be "full" with free space?
8. What does **uptime** tell you during troubleshooting?
9. What is the difference between **GB** and **GiB**?
10. What is an **exit code**? What does `0` mean?
11. Why should a diagnostic tool run **without root**? (principle of least privilege)
12. Why is a hostname considered **sensitive** information?
13. What is a **unit test**? Why use **mocks**?
14. Why return `None` instead of `0` when a value is missing?
15. What is **JSON** and why is it useful for automation?
