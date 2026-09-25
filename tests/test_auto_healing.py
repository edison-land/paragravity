"""Tests for Auto-Healing & Update Isolation across AntiGravity updates (Issue #12).

Verifies:
1. Zero Data Loss: Cookies, Local Storage, Tokens, and configurations are NEVER touched.
2. Stale Lock Cleaning: Orphaned SingletonLock, SingletonSocket, DevToolsActivePort, run.pid.
3. Sandbox Update Suppression: autoCheckForUpdates=false in app_storage.json, update.mode=none in settings.json.
4. Ephemeral Cache Purge: V8 Code Cache & GPUCache safely purged on version mismatch or force.
5. Doctor Command: CLI diagnostics and automated --fix repair.
"""

import contextlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "bin" / "paragravity"
IS_WINDOWS = sys.platform == "win32"
IS_DARWIN = sys.platform == "darwin"


def load_cli_module():
    loader = importlib.machinery.SourceFileLoader("paragravity_cli_healing", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@contextlib.contextmanager
def sandbox_home():
    with tempfile.TemporaryDirectory(prefix="pgrav-heal-test-") as tmp:
        home = Path(tmp)
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
        env["APPDATA"] = str(home / "AppData" / "Roaming")
        env["PARAGRAVITY_PROFILES_DIR"] = str(home / ".antigravity-profiles")
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        yield home, env


def run_cli(args, env, stdin=subprocess.DEVNULL):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env, stdin=stdin, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )


class AutoHealingUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli_module()

    def test_clean_stale_locks_removes_locks_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "test_profile"
            data_dir = pdir / "data"
            data_dir.mkdir(parents=True)

            # Create mock locks and sockets
            lock = data_dir / "SingletonLock"
            sock = data_dir / "SingletonSocket"
            cookie_lock = data_dir / "SingletonCookie"
            port_file = data_dir / "DevToolsActivePort"
            pid_file = pdir / "run.pid"

            lock.write_text("dummy-lock-content")
            sock.write_text("dummy-socket")
            cookie_lock.write_text("dummy-cookie-lock")
            port_file.write_text("12345\n/devtools/browser/xyz")
            pid_file.write_text("99999999")  # non-existent PID

            # Critical user data that MUST be preserved
            cookies = data_dir / "Cookies"
            cookies.write_bytes(b"oauth-session-token-bytes")
            local_storage = data_dir / "Local Storage"
            local_storage.mkdir()
            (local_storage / "000003.log").write_text("active-session")
            app_storage = data_dir / "app_storage.json"
            app_storage.write_text(json.dumps({"jetski.login": "user@gmail.com"}))

            cleaned = self.cli.clean_stale_locks(pdir, data_dir)
            self.assertIn("SingletonLock", cleaned)
            self.assertIn("SingletonSocket", cleaned)
            self.assertIn("SingletonCookie", cleaned)
            self.assertIn("DevToolsActivePort", cleaned)
            self.assertIn("run.pid", cleaned)

            # Assert locks are gone
            self.assertFalse(lock.exists())
            self.assertFalse(sock.exists())
            self.assertFalse(cookie_lock.exists())
            self.assertFalse(port_file.exists())
            self.assertFalse(pid_file.exists())

            # Zero Data Loss: assert user data is 100% preserved
            self.assertTrue(cookies.exists())
            self.assertEqual(cookies.read_bytes(), b"oauth-session-token-bytes")
            self.assertTrue((local_storage / "000003.log").exists())
            self.assertTrue(app_storage.exists())

    def test_clean_stale_locks_skips_when_process_is_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "running_profile"
            data_dir = pdir / "data"
            data_dir.mkdir(parents=True)

            lock = data_dir / "SingletonLock"
            lock.write_text("running-instance-lock")
            pid_file = pdir / "run.pid"
            # Set to current Python test runner process PID
            pid_file.write_text(str(os.getpid()))

            cleaned = self.cli.clean_stale_locks(pdir, data_dir)
            self.assertEqual(cleaned, [])
            self.assertTrue(lock.exists())
            self.assertTrue(pid_file.exists())

    def test_suppress_sandbox_autoupdate_isolates_updater_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profile"
            data_dir = pdir / "data"
            user_dir = data_dir / "User"
            data_dir.mkdir(parents=True)
            user_dir.mkdir(parents=True)

            # Existing state with pre-existing user data
            app_storage = data_dir / "app_storage.json"
            app_storage.write_text(json.dumps({
                "jetski.onboarding.lastLoginUsername": "alice@gmail.com",
                "customSetting": "preservedValue",
            }))
            user_settings = user_dir / "settings.json"
            user_settings.write_text(json.dumps({
                "editor.fontSize": 14,
            }))

            mod = self.cli.suppress_sandbox_autoupdate(pdir)
            self.assertTrue(mod)

            # Check app_storage.json
            storage_data = json.loads(app_storage.read_text(encoding="utf-8"))
            self.assertEqual(storage_data.get("autoCheckForUpdates"), "false")
            self.assertEqual(storage_data.get("jetski.onboarding.lastLoginUsername"), "alice@gmail.com")
            self.assertEqual(storage_data.get("customSetting"), "preservedValue")

            # Check User/settings.json
            settings_data = json.loads(user_settings.read_text(encoding="utf-8"))
            self.assertEqual(settings_data.get("update.mode"), "none")
            self.assertEqual(settings_data.get("editor.fontSize"), 14)

    def test_heal_profile_environment_purges_ephemeral_caches_on_version_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profile"
            data_dir = pdir / "data"
            code_cache = data_dir / "Code Cache" / "js"
            gpu_cache = data_dir / "GPUCache"
            cache_dir = data_dir / "Cache"
            code_cache.mkdir(parents=True)
            gpu_cache.mkdir(parents=True)
            cache_dir.mkdir(parents=True)

            (code_cache / "old_v8_bytecode.bin").write_text("v8-bytecode-data")
            (gpu_cache / "gpu_blob.bin").write_text("gpu-data")
            (cache_dir / "cached_resource.bin").write_text("cache-data")

            # Write old version in profile.json
            profile_meta = pdir / "profile.json"
            profile_meta.write_text(json.dumps({
                "name": "profile",
                "last_app_version": "2.15.0",
            }))

            # Mock get_installed_app_version to return "2.16.0"
            with patch.object(self.cli, "get_installed_app_version", return_value="2.16.0"):
                report = self.cli.heal_profile_environment(pdir, force=False)

            self.assertTrue(report["version_changed"])
            self.assertEqual(report["old_version"], "2.15.0")
            self.assertEqual(report["new_version"], "2.16.0")
            self.assertIn("Code Cache", report["caches_purged"])
            self.assertIn("GPUCache", report["caches_purged"])
            self.assertIn("Cache", report["caches_purged"])

            # Caches are cleared
            self.assertFalse((data_dir / "Code Cache").exists())
            self.assertFalse(gpu_cache.exists())
            self.assertFalse(cache_dir.exists())

            # Profile meta version is updated
            new_meta = json.loads(profile_meta.read_text(encoding="utf-8"))
            self.assertEqual(new_meta.get("last_app_version"), "2.16.0")

    def test_heal_profile_environment_skips_purge_when_version_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profile"
            data_dir = pdir / "data"
            code_cache = data_dir / "Code Cache"
            code_cache.mkdir(parents=True)
            canary = code_cache / "valid.bin"
            canary.write_text("keep-valid-cache")

            profile_meta = pdir / "profile.json"
            profile_meta.write_text(json.dumps({
                "name": "profile",
                "last_app_version": "2.16.0",
            }))

            with patch.object(self.cli, "get_installed_app_version", return_value="2.16.0"):
                report = self.cli.heal_profile_environment(pdir, force=False)

            self.assertFalse(report["version_changed"])
            self.assertEqual(report["caches_purged"], [])
            self.assertTrue(canary.exists())


class DoctorCliIntegrationTests(unittest.TestCase):
    def test_doctor_diagnoses_and_fixes_issues(self):
        with sandbox_home() as (home, env):
            profiles_dir = Path(env["PARAGRAVITY_PROFILES_DIR"])
            pdir = profiles_dir / "devbox"
            data_dir = pdir / "data"
            data_dir.mkdir(parents=True)

            # Create profile metadata without last_app_version
            (pdir / "profile.json").write_text(json.dumps({"name": "devbox", "version": 1}))

            # Inject stale lock
            (data_dir / "SingletonLock").write_text("stale-lock")
            (data_dir / "DevToolsActivePort").write_text("9222\n")

            # 1. Run doctor (diagnosis only)
            res1 = run_cli(["doctor", "--json"], env)
            self.assertEqual(res1.returncode, 0, res1.stderr)
            diag = json.loads(res1.stdout)
            self.assertIn("devbox", diag["profiles"])
            self.assertGreater(diag["issues_found"], 0)
            self.assertIn("SingletonLock", diag["profiles"]["devbox"]["stale_locks"])

            # 2. Run doctor --fix
            res2 = run_cli(["doctor", "--fix"], env)
            self.assertEqual(res2.returncode, 0, res2.stderr)
            self.assertIn("Healed:", res2.stdout)

            # 3. Verify health after repair
            res3 = run_cli(["doctor", "--json"], env)
            self.assertEqual(res3.returncode, 0, res3.stderr)
            repaired = json.loads(res3.stdout)
            self.assertEqual(repaired["issues_found"], 0)
            self.assertFalse((data_dir / "SingletonLock").exists())

    def test_launch_command_auto_heals_stale_locks(self):
        with sandbox_home() as (home, env):
            # Create a mock antigravity binary that echoes and exits
            if IS_WINDOWS:
                mock_bin = home / "mock_antigravity.cmd"
                mock_bin.write_text("@echo off\nexit /b 0\n")
            else:
                mock_bin = home / "mock_antigravity"
                mock_bin.write_text("#!/bin/sh\nexit 0\n")
                mock_bin.chmod(0o755)
            env["ANTIGRAVITY_BIN"] = str(mock_bin)

            profiles_dir = Path(env["PARAGRAVITY_PROFILES_DIR"])
            pdir = profiles_dir / "testbox"
            data_dir = pdir / "data"
            data_dir.mkdir(parents=True)
            (pdir / "profile.json").write_text(json.dumps({"name": "testbox", "version": 1}))

            stale_lock = data_dir / "SingletonLock"
            stale_lock.write_text("leftover-lock")

            res = run_cli(["launch", "testbox", "--foreground"], env)
            self.assertEqual(res.returncode, 0, res.stderr)
            # The stale lock must have been cleaned before or during launch
            self.assertFalse(stale_lock.exists())


if __name__ == "__main__":
    unittest.main()
