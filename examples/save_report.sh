#!/usr/bin/env bash
# Save a system information report as a JSON file.
#
# Usage (from the project root folder):
#   bash examples/save_report.sh
#
# The file is saved in the "reports" folder, for example:
#   reports/system-report-2026-01-15_14-30-00.json
#
# The hostname is redacted, so the file is safer to attach to a ticket.
# The "reports" folder is listed in .gitignore, so reports are never
# committed to Git by accident.

set -euo pipefail   # stop on errors, unset variables and pipe failures

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/reports"
REPORT_FILE="${REPORT_DIR}/system-report-$(date +%Y-%m-%d_%H-%M-%S).json"

mkdir -p "${REPORT_DIR}"

PYTHONPATH="${PROJECT_ROOT}/src" python3 -m linux_diagnostics --json --redact > "${REPORT_FILE}"

echo "Report saved to: ${REPORT_FILE}"
