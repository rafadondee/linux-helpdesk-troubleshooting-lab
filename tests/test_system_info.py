"""Tests for MODULE 01 - linux_diagnostics.system_info.

The tests never depend on the real computer. They use:
- temporary files that imitate /etc/os-release, /proc/meminfo, etc.;
- unittest.mock to replace functions like shutil.disk_usage().
So the same tests pass on any Linux machine (and even on Windows/macOS).
"""

import os
import tempfile
import unittest
from collections import namedtuple
from unittest import mock

from linux_diagnostics import system_info

DiskUsage = namedtuple("DiskUsage", "total used free")

SAMPLE_OS_RELEASE = """\
PRETTY_NAME="Ubuntu 25.04"
NAME="Ubuntu"
VERSION_ID="25.04"
VERSION="25.04 (Plucky Puffin)"
ID=ubuntu
"""

SAMPLE_CPUINFO_X86 = """\
processor\t: 0
vendor_id\t: GenuineIntel
model name\t: Example CPU Model @ 2.40GHz

processor\t: 1
vendor_id\t: GenuineIntel
model name\t: Example CPU Model @ 2.40GHz
"""

SAMPLE_CPUINFO_ARM = """\
processor\t: 0
BogoMIPS\t: 108.00

Hardware\t: BCM2835
Model\t\t: Example Pi 4 Model B
"""

SAMPLE_MEMINFO = """\
MemTotal:        8000000 kB
MemFree:         1000000 kB
MemAvailable:    6000000 kB
Buffers:          200000 kB
Cached:          3000000 kB
"""

SAMPLE_MEMINFO_OLD_KERNEL = """\
MemTotal:        4000000 kB
MemFree:         1000000 kB
Buffers:          500000 kB
Cached:           500000 kB
"""


class TempFileTestCase(unittest.TestCase):
    """Base class that creates fake system files in a temporary folder."""

    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.folder = self._folder.name

    def tearDown(self):
        self._folder.cleanup()

    def make_file(self, name, content):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def missing_path(self, name="missing"):
        return os.path.join(self.folder, name)


# ---------------------------------------------------------------------------
# Operating system
# ---------------------------------------------------------------------------

class TestDistributionInfo(TempFileTestCase):
    def test_reads_os_release(self):
        path = self.make_file("os-release", SAMPLE_OS_RELEASE)
        info = system_info.get_distribution_info([path])
        self.assertEqual(info["name"], "Ubuntu")
        self.assertEqual(info["version"], "25.04 (Plucky Puffin)")
        self.assertEqual(info["pretty_name"], "Ubuntu 25.04")

    def test_uses_version_id_when_version_is_missing(self):
        path = self.make_file("os-release", 'NAME="Debian GNU/Linux"\nVERSION_ID="12"\n')
        self.assertEqual(system_info.get_distribution_info([path])["version"], "12")

    def test_falls_back_to_second_path(self):
        second = self.make_file("os-release", SAMPLE_OS_RELEASE)
        info = system_info.get_distribution_info([self.missing_path(), second])
        self.assertEqual(info["name"], "Ubuntu")

    def test_missing_file_returns_none_values(self):
        info = system_info.get_distribution_info([self.missing_path()])
        self.assertEqual(info, {"name": None, "version": None, "pretty_name": None})


class TestKernelAndHostname(unittest.TestCase):
    @mock.patch("linux_diagnostics.system_info.platform.release", return_value="6.14.0-15-generic")
    def test_kernel_version(self, _mock_release):
        self.assertEqual(system_info.get_kernel_version(), "6.14.0-15-generic")

    @mock.patch("linux_diagnostics.system_info.platform.release", return_value="")
    def test_empty_kernel_version_is_none(self, _mock_release):
        self.assertIsNone(system_info.get_kernel_version())

    @mock.patch("linux_diagnostics.system_info.socket.gethostname", return_value="test-host")
    def test_hostname(self, _mock_hostname):
        self.assertEqual(system_info.get_hostname(), "test-host")


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

class TestCpuInfo(TempFileTestCase):
    def test_x86_model_name(self):
        path = self.make_file("cpuinfo", SAMPLE_CPUINFO_X86)
        self.assertEqual(system_info.get_cpu_model(path), "Example CPU Model @ 2.40GHz")

    def test_arm_model(self):
        path = self.make_file("cpuinfo", SAMPLE_CPUINFO_ARM)
        self.assertEqual(system_info.get_cpu_model(path), "Example Pi 4 Model B")

    @mock.patch("linux_diagnostics.system_info.platform.processor", return_value="x86_64")
    def test_missing_cpuinfo_uses_platform_fallback(self, _mock_processor):
        self.assertEqual(system_info.get_cpu_model(self.missing_path()), "x86_64")

    @mock.patch("linux_diagnostics.system_info.platform.processor", return_value="")
    def test_no_information_returns_none(self, _mock_processor):
        self.assertIsNone(system_info.get_cpu_model(self.missing_path()))

    @mock.patch("linux_diagnostics.system_info.os.cpu_count", return_value=8)
    def test_logical_cores(self, _mock_count):
        self.assertEqual(system_info.get_logical_cpu_count(), 8)

    @mock.patch("linux_diagnostics.system_info.os.cpu_count", return_value=None)
    def test_logical_cores_unknown(self, _mock_count):
        self.assertIsNone(system_info.get_logical_cpu_count())


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class TestMemoryInfo(TempFileTestCase):
    def test_memory_values_and_percentage(self):
        path = self.make_file("meminfo", SAMPLE_MEMINFO)
        memory = system_info.get_memory_info(path)
        self.assertEqual(memory["total_bytes"], 8000000 * 1024)
        self.assertEqual(memory["available_bytes"], 6000000 * 1024)
        self.assertEqual(memory["used_bytes"], 2000000 * 1024)
        self.assertEqual(memory["usage_percent"], 25.0)
        self.assertFalse(memory["available_is_estimate"])

    def test_old_kernel_without_memavailable_is_estimated(self):
        path = self.make_file("meminfo", SAMPLE_MEMINFO_OLD_KERNEL)
        memory = system_info.get_memory_info(path)
        # 1000000 + 500000 + 500000 = 2000000 kB available
        self.assertEqual(memory["available_bytes"], 2000000 * 1024)
        self.assertEqual(memory["usage_percent"], 50.0)
        self.assertTrue(memory["available_is_estimate"])

    def test_missing_meminfo_returns_none_values(self):
        memory = system_info.get_memory_info(self.missing_path())
        self.assertIsNone(memory["total_bytes"])
        self.assertIsNone(memory["available_bytes"])
        self.assertIsNone(memory["used_bytes"])
        self.assertIsNone(memory["usage_percent"])

    def test_invalid_number_is_ignored(self):
        path = self.make_file("meminfo", "MemTotal: abc kB\nMemAvailable: 100 kB\n")
        memory = system_info.get_memory_info(path)
        self.assertIsNone(memory["total_bytes"])
        self.assertEqual(memory["available_bytes"], 100 * 1024)
        self.assertIsNone(memory["usage_percent"])

    def test_calculate_memory_usage(self):
        result = system_info.calculate_memory_usage(1000, 250)
        self.assertEqual(result, {"used_bytes": 750, "usage_percent": 75.0})

    def test_calculate_memory_usage_never_negative(self):
        # Available bigger than total should never happen, but must not break.
        self.assertEqual(system_info.calculate_memory_usage(100, 150)["used_bytes"], 0)

    def test_calculate_memory_usage_with_zero_total(self):
        self.assertIsNone(system_info.calculate_memory_usage(0, 0)["usage_percent"])


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

class TestDiskInfo(unittest.TestCase):
    @mock.patch("linux_diagnostics.system_info.shutil.disk_usage")
    def test_disk_values(self, mock_disk_usage):
        mock_disk_usage.return_value = DiskUsage(total=100 * 1024 ** 3, used=40 * 1024 ** 3, free=60 * 1024 ** 3)
        disk = system_info.get_disk_info("/")
        mock_disk_usage.assert_called_once_with("/")
        self.assertEqual(disk["path"], "/")
        self.assertEqual(disk["total_bytes"], 100 * 1024 ** 3)
        self.assertEqual(disk["free_bytes"], 60 * 1024 ** 3)
        self.assertEqual(disk["used_bytes"], 40 * 1024 ** 3)
        self.assertEqual(disk["usage_percent"], 40.0)

    @mock.patch("linux_diagnostics.system_info.shutil.disk_usage")
    def test_usage_percent_ignores_reserved_blocks_like_df(self, mock_disk_usage):
        # total 100, used 50, free for users 45 -> 5 reserved for root.
        mock_disk_usage.return_value = DiskUsage(total=100, used=50, free=45)
        self.assertEqual(system_info.get_disk_info("/")["usage_percent"], 52.6)

    def test_calculate_disk_usage_empty_filesystem(self):
        self.assertIsNone(system_info.calculate_disk_usage(0, 0))

    @mock.patch("linux_diagnostics.system_info.shutil.disk_usage", side_effect=FileNotFoundError("no such path"))
    def test_missing_path_raises(self, _mock_disk_usage):
        with self.assertRaises(FileNotFoundError):
            system_info.get_disk_info("/does/not/exist")


# ---------------------------------------------------------------------------
# Uptime
# ---------------------------------------------------------------------------

class TestUptime(TempFileTestCase):
    def test_reads_first_number(self):
        path = self.make_file("uptime", "93784.52 350000.10\n")
        self.assertEqual(system_info.get_uptime_seconds(path), 93784.52)

    def test_missing_file(self):
        self.assertIsNone(system_info.get_uptime_seconds(self.missing_path()))

    def test_invalid_content(self):
        path = self.make_file("uptime", "not-a-number\n")
        self.assertIsNone(system_info.get_uptime_seconds(path))

    def test_empty_file(self):
        path = self.make_file("uptime", "")
        self.assertIsNone(system_info.get_uptime_seconds(path))


# ---------------------------------------------------------------------------
# Full collection
# ---------------------------------------------------------------------------

def _patch_all_collectors(**overrides):
    """Patch every collector with fake data. Keyword args replace defaults."""
    defaults = {
        "get_distribution_info": mock.Mock(return_value={
            "name": "Ubuntu", "version": "25.04", "pretty_name": "Ubuntu 25.04"}),
        "get_kernel_version": mock.Mock(return_value="6.14.0-15-generic"),
        "get_hostname": mock.Mock(return_value="test-host"),
        "get_cpu_model": mock.Mock(return_value="Example CPU"),
        "get_logical_cpu_count": mock.Mock(return_value=4),
        "get_memory_info": mock.Mock(return_value={
            "total_bytes": 1000, "available_bytes": 400, "used_bytes": 600,
            "usage_percent": 60.0, "available_is_estimate": False}),
        "get_disk_info": mock.Mock(return_value={
            "path": "/", "total_bytes": 2000, "free_bytes": 500,
            "used_bytes": 1500, "usage_percent": 75.0}),
        "get_uptime_seconds": mock.Mock(return_value=3600.0),
    }
    defaults.update(overrides)
    patchers = [mock.patch.object(system_info, name, new) for name, new in defaults.items()]
    patchers.append(mock.patch.object(system_info.platform, "system", return_value="Linux"))
    return patchers


class TestCollectSystemInfo(unittest.TestCase):
    def run_collect(self, **overrides):
        patchers = _patch_all_collectors(**overrides)
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        return system_info.collect_system_info()

    def test_complete_report_has_all_twelve_items(self):
        info = self.run_collect()
        self.assertEqual(info["os"]["distribution"], "Ubuntu")          # 1
        self.assertEqual(info["os"]["version"], "25.04")                # 1
        self.assertEqual(info["os"]["kernel"], "6.14.0-15-generic")     # 2
        self.assertEqual(info["os"]["hostname"], "test-host")          # 3
        self.assertEqual(info["cpu"]["model"], "Example CPU")           # 4
        self.assertEqual(info["cpu"]["logical_cores"], 4)               # 5
        self.assertEqual(info["memory"]["total_bytes"], 1000)           # 6
        self.assertEqual(info["memory"]["available_bytes"], 400)        # 7
        self.assertEqual(info["memory"]["usage_percent"], 60.0)         # 8
        self.assertEqual(info["disk"]["total_bytes"], 2000)             # 9
        self.assertEqual(info["disk"]["free_bytes"], 500)               # 10
        self.assertEqual(info["disk"]["usage_percent"], 75.0)           # 11
        self.assertEqual(info["uptime"]["seconds"], 3600.0)             # 12
        self.assertEqual(info["warnings"], [])
        self.assertEqual(info["tool"]["module"], "system_info")

    def test_missing_values_create_warnings(self):
        info = self.run_collect(
            get_hostname=mock.Mock(return_value=None),
            get_uptime_seconds=mock.Mock(return_value=None),
        )
        self.assertIsNone(info["os"]["hostname"])
        self.assertIn("Hostname: information not available", info["warnings"])
        self.assertIn("System uptime: information not available", info["warnings"])

    def test_exception_in_one_collector_does_not_break_report(self):
        info = self.run_collect(
            get_disk_info=mock.Mock(side_effect=PermissionError("access denied")),
        )
        # Disk values become None, but the rest of the report is still there.
        self.assertIsNone(info["disk"]["total_bytes"])
        self.assertEqual(info["cpu"]["model"], "Example CPU")
        self.assertTrue(any("PermissionError" in w for w in info["warnings"]))

    def test_unexpected_exception_in_cpu_collector(self):
        info = self.run_collect(get_cpu_model=mock.Mock(side_effect=RuntimeError("boom")))
        self.assertIsNone(info["cpu"]["model"])
        self.assertTrue(any("CPU model: could not be collected" in w for w in info["warnings"]))

    def test_estimated_memory_creates_warning(self):
        info = self.run_collect(get_memory_info=mock.Mock(return_value={
            "total_bytes": 1000, "available_bytes": 500, "used_bytes": 500,
            "usage_percent": 50.0, "available_is_estimate": True}))
        self.assertTrue(any("estimated" in w for w in info["warnings"]))

    def test_non_linux_system_creates_warning(self):
        patchers = _patch_all_collectors()
        patchers[-1] = mock.patch.object(system_info.platform, "system", return_value="Windows")
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        info = system_info.collect_system_info()
        self.assertTrue(any("designed for Linux" in w for w in info["warnings"]))

    def test_custom_disk_path_is_used(self):
        disk_mock = mock.Mock(return_value={
            "path": "/home", "total_bytes": 1, "free_bytes": 1,
            "used_bytes": 0, "usage_percent": 0.0})
        patchers = _patch_all_collectors(get_disk_info=disk_mock)
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        system_info.collect_system_info(disk_path="/home")
        disk_mock.assert_called_once_with("/home")


if __name__ == "__main__":
    unittest.main()
