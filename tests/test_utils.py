"""Tests for the helper functions in linux_diagnostics.utils."""

import os
import tempfile
import unittest

from linux_diagnostics import utils


class TestReadTextFile(unittest.TestCase):
    def test_reads_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sample.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("hello")
            self.assertEqual(utils.read_text_file(path), "hello")

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(utils.read_text_file(os.path.join(folder, "missing.txt")))


class TestParseKeyValueLines(unittest.TestCase):
    def test_equals_separator_removes_quotes(self):
        text = 'NAME="Ubuntu"\nVERSION_ID=\'25.04\'\n# comment\n\ninvalid line\n'
        self.assertEqual(
            utils.parse_key_value_lines(text, "="),
            {"NAME": "Ubuntu", "VERSION_ID": "25.04"},
        )

    def test_colon_separator_and_first_value_wins(self):
        text = "model name\t: CPU A\nmodel name\t: CPU B\n"
        self.assertEqual(utils.parse_key_value_lines(text, ":"), {"model name": "CPU A"})

    def test_value_may_contain_separator(self):
        self.assertEqual(utils.parse_key_value_lines("URL=http://a=b", "="), {"URL": "http://a=b"})


class TestCalculatePercentage(unittest.TestCase):
    def test_normal_value(self):
        self.assertEqual(utils.calculate_percentage(25, 100), 25.0)

    def test_rounds_to_one_decimal(self):
        self.assertEqual(utils.calculate_percentage(1, 3), 33.3)

    def test_zero_total_returns_none(self):
        self.assertIsNone(utils.calculate_percentage(10, 0))

    def test_missing_values_return_none(self):
        self.assertIsNone(utils.calculate_percentage(None, 100))
        self.assertIsNone(utils.calculate_percentage(10, None))


class TestFormatBytes(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(utils.format_bytes(512), "512 B")

    def test_kib(self):
        self.assertEqual(utils.format_bytes(1536), "1.5 KiB")

    def test_gib(self):
        self.assertEqual(utils.format_bytes(8 * 1024 ** 3), "8.0 GiB")

    def test_none_and_negative(self):
        self.assertEqual(utils.format_bytes(None), utils.UNAVAILABLE)
        self.assertEqual(utils.format_bytes(-1), utils.UNAVAILABLE)


class TestFormatDuration(unittest.TestCase):
    def test_days_hours_minutes(self):
        seconds = 2 * 86400 + 3 * 3600 + 15 * 60 + 30
        self.assertEqual(utils.format_duration(seconds), "2 days, 3 hours, 15 minutes")

    def test_singular_words(self):
        self.assertEqual(utils.format_duration(86400 + 3600 + 60), "1 day, 1 hour, 1 minute")

    def test_less_than_one_minute(self):
        self.assertEqual(utils.format_duration(42), "less than 1 minute")

    def test_none(self):
        self.assertEqual(utils.format_duration(None), utils.UNAVAILABLE)


class TestDisplayHelpers(unittest.TestCase):
    def test_format_percentage(self):
        self.assertEqual(utils.format_percentage(42.25), "42.2%")
        self.assertEqual(utils.format_percentage(None), utils.UNAVAILABLE)

    def test_display_value(self):
        self.assertEqual(utils.display_value(8), "8")
        self.assertEqual(utils.display_value(None), utils.UNAVAILABLE)
        self.assertEqual(utils.display_value(""), utils.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
