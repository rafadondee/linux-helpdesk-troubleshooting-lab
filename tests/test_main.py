"""Tests for the command-line interface in linux_diagnostics.main."""

import contextlib
import io
import json
import unittest
from unittest import mock

from linux_diagnostics import __version__, main

FAKE_INFO = {
    "tool": {"name": "linux-diagnostics", "version": __version__, "module": "system_info"},
    "collected_at": "2026-01-01T12:00:00+00:00",
    "os": {"distribution": "Ubuntu", "version": "25.04", "pretty_name": "Ubuntu 25.04",
           "kernel": "6.14.0-15-generic", "hostname": "test-host"},
    "cpu": {"model": "Example CPU", "logical_cores": 4},
    "memory": {"total_bytes": 8 * 1024 ** 3, "available_bytes": 6 * 1024 ** 3,
               "used_bytes": 2 * 1024 ** 3, "usage_percent": 25.0,
               "available_is_estimate": False},
    "disk": {"path": "/", "total_bytes": 100 * 1024 ** 3, "free_bytes": 60 * 1024 ** 3,
             "used_bytes": 40 * 1024 ** 3, "usage_percent": 40.0},
    "uptime": {"seconds": 90000.0},
    "warnings": [],
}


def run_cli(args, info=FAKE_INFO, side_effect=None):
    """Run main() with fake data and return (exit_code, stdout, stderr)."""
    stdout, stderr = io.StringIO(), io.StringIO()
    collect_mock = mock.Mock(return_value=info, side_effect=side_effect)
    with mock.patch.object(main, "collect_system_info", collect_mock), \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = main.main(args)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class TestTextOutput(unittest.TestCase):
    def test_text_report_contains_all_sections(self):
        exit_code, output, _ = run_cli([])
        self.assertEqual(exit_code, main.EXIT_SUCCESS)
        for section in ("[Operating System]", "[CPU]", "[Memory (RAM)]", "[Disk (/)]", "[Uptime]"):
            self.assertIn(section, output)
        self.assertIn("Ubuntu", output)
        self.assertIn("8.0 GiB", output)
        self.assertIn("25.0%", output)
        self.assertIn("1 day, 1 hour", output)
        self.assertNotIn("[Warnings]", output)

    def test_missing_values_show_unavailable(self):
        info = json.loads(json.dumps(FAKE_INFO))
        info["cpu"]["model"] = None
        info["memory"]["total_bytes"] = None
        info["warnings"] = ["CPU model: information not available"]
        _, output, _ = run_cli([], info=info)
        self.assertIn("Model            : Unavailable", output)
        self.assertIn("[Warnings]", output)
        self.assertIn("CPU model: information not available", output)


class TestJsonOutput(unittest.TestCase):
    def test_json_is_valid_and_complete(self):
        exit_code, output, _ = run_cli(["--json"])
        self.assertEqual(exit_code, main.EXIT_SUCCESS)
        data = json.loads(output)  # raises an error if the JSON is invalid
        self.assertEqual(data["cpu"]["logical_cores"], 4)
        self.assertEqual(data["memory"]["usage_percent"], 25.0)
        self.assertEqual(data["os"]["hostname"], "test-host")

    def test_none_becomes_json_null(self):
        info = json.loads(json.dumps(FAKE_INFO))
        info["uptime"]["seconds"] = None
        _, output, _ = run_cli(["--json"], info=info)
        self.assertIn('"seconds": null', output)
        self.assertIsNone(json.loads(output)["uptime"]["seconds"])

    def test_redact_hides_hostname(self):
        _, output, _ = run_cli(["--json", "--redact"])
        self.assertEqual(json.loads(output)["os"]["hostname"], main.REDACTED)
        self.assertNotIn("test-host", output)

    def test_redact_does_not_change_original_data(self):
        main.redact_sensitive_data(FAKE_INFO)
        self.assertEqual(FAKE_INFO["os"]["hostname"], "test-host")


class TestOptions(unittest.TestCase):
    def test_version(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as context:
            main.main(["--version"])
        self.assertEqual(context.exception.code, 0)
        self.assertIn(__version__, stdout.getvalue())

    def test_help(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as context:
            main.main(["--help"])
        self.assertEqual(context.exception.code, 0)
        for option in ("--json", "--version", "--disk-path", "--redact"):
            self.assertIn(option, stdout.getvalue())

    def test_invalid_option_exits_with_code_2(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as context:
            main.main(["--not-an-option"])
        self.assertEqual(context.exception.code, 2)

    def test_disk_path_is_passed_to_collector(self):
        collect_mock = mock.Mock(return_value=FAKE_INFO)
        with mock.patch.object(main, "collect_system_info", collect_mock), \
                contextlib.redirect_stdout(io.StringIO()):
            main.main(["--disk-path", "/home"])
        collect_mock.assert_called_once_with(disk_path="/home")


class TestErrorHandling(unittest.TestCase):
    def test_unexpected_error_returns_exit_code_1(self):
        exit_code, output, error = run_cli([], side_effect=RuntimeError("something broke"))
        self.assertEqual(exit_code, main.EXIT_ERROR)
        self.assertEqual(output, "")
        self.assertIn("something broke", error)

    def test_unexpected_error_with_json_writes_json_error(self):
        exit_code, _, error = run_cli(["--json"], side_effect=RuntimeError("something broke"))
        self.assertEqual(exit_code, main.EXIT_ERROR)
        self.assertIn("something broke", json.loads(error)["error"])

    def test_keyboard_interrupt(self):
        exit_code, _, error = run_cli([], side_effect=KeyboardInterrupt())
        self.assertEqual(exit_code, main.EXIT_INTERRUPTED)
        self.assertIn("Interrupted", error)


if __name__ == "__main__":
    unittest.main()
