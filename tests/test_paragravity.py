"""Stdlib-only test suite for the `bin/paragravity` CLI.

Every test runs the real CLI in a sandboxed $HOME (via PARAGRAVITY_PROFILES_DIR
and HOME overrides), so nothing here touches the developer's real profiles or
~/Applications.
"""

import contextlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "bin" / "paragravity"
IS_DARWIN = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# Names that must be rejected by validate_profile_name (command injection,
# path traversal, glob/glob-metachar abuse).
DANGEROUS_NAMES = [
    "..", ".", "a/b", "$(id)", "`id`", "${IFS}x", "x';'", "zwe)copy",
    "x y", "-x", "`touch${IFS}${TMPDIR}pwned`",
]


def load_cli_module():
    loader = importlib.machinery.SourceFileLoader("paragravity_cli", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                return exit_code.value == 259
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            return str(pid) in (res.stdout or "")
        except Exception:
            pass
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, SystemError):
        return False


def is_link_or_junction(p: Path) -> bool:
    if p.is_symlink():
        return True
    if IS_WINDOWS:
        if hasattr(os.path, "isjunction") and os.path.isjunction(p):
            return True
        try:
            return bool(os.readlink(p))
        except (OSError, ValueError):
            pass
        try:
            import stat
            return bool(p.stat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        except Exception:
            pass
    return False


def wait_until(predicate, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


@contextlib.contextmanager
def sandbox_home():
    with tempfile.TemporaryDirectory(prefix="pgrav-test-") as tmp:
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
        encoding="utf-8", errors="replace", timeout=120,
    )


class ProfileNameValidationTests(unittest.TestCase):
    """Regression tests for the command-injection / path-traversal fixes."""

    def test_create_rejects_dangerous_names(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            for name in DANGEROUS_NAMES:
                with self.subTest(name=name):
                    result = run_cli(["create", name], env)
                    # argparse may exit 2 for option-looking names ("-x"); our
                    # validation exits 1. Either way nothing may be created.
                    self.assertNotEqual(result.returncode, 0, result)
                    if result.returncode == 1:
                        self.assertIn("Invalid profile name", result.stderr + result.stdout)
                    # No profile metadata may be written anywhere for rejected names
                    self.assertFalse((profiles / name / "profile.json").exists(), result)

    def test_delete_rejects_traversal_names(self):
        with sandbox_home() as (home, env):
            canary = home / "important.txt"
            canary.write_text("keep me")
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            profiles.mkdir(parents=True, exist_ok=True)

            for name in ("..", "."):
                with self.subTest(name=name):
                    result = run_cli(["delete", name, "--force"], env)
                    self.assertEqual(result.returncode, 1, result)
            self.assertTrue(canary.exists(), "delete must not escape the profiles dir")
            self.assertTrue(profiles.exists())

    def test_injection_poc_produces_no_launcher(self):
        with sandbox_home() as (home, env):
            marker = home / "pwned_marker"
            name = f"`touch${{IFS}}{marker.name}`"
            result = run_cli(["create", name], env)
            self.assertEqual(result.returncode, 1, result)
            self.assertFalse(marker.exists(), "injected command must never run")
            apps = home / "Applications"
            if apps.is_dir():
                self.assertEqual(list(apps.glob("*.app")), [], "no launcher may be generated")


class PromptSafetyTests(unittest.TestCase):

    def test_delete_prompt_eof_aborts(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "victim"], env).returncode, 0)
            result = run_cli(["delete", "victim"], env)  # stdin=DEVNULL -> EOF
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("Aborted", result.stdout)
            self.assertTrue(Path(env["PARAGRAVITY_PROFILES_DIR"], "victim").exists())

    def test_launch_missing_profile_eof_exits_cleanly(self):
        with sandbox_home() as (_, env):
            result = run_cli(["launch", "ghost"], env)  # stdin=DEVNULL -> EOF
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.returncode, 1)


class BasicLifecycleTests(unittest.TestCase):

    def test_create_list_info_path_delete_roundtrip(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])

            self.assertEqual(run_cli(["create", "zwe", "-d", "demo"], env).returncode, 0)
            self.assertTrue((profiles / "zwe" / "profile.json").is_file())

            listed = run_cli(["list"], env)
            self.assertEqual(listed.returncode, 0)
            self.assertIn("zwe", listed.stdout or "")

            info = run_cli(["info", "zwe"], env)
            self.assertIn("Profile: zwe", info.stdout)

            path = run_cli(["path", "zwe"], env)
            # `pgrav path` prints the fully resolved path (/var -> /private/var on macOS)
            self.assertEqual(path.stdout.strip(), str((profiles / "zwe").resolve()))

            self.assertEqual(run_cli(["delete", "zwe", "--force"], env).returncode, 0)
            self.assertFalse((profiles / "zwe").exists())

    def test_delete_removes_only_exact_bundle(self):
        if not IS_DARWIN:
            self.skipTest("macOS .app bundles only")
        with sandbox_home() as (home, env):
            apps = home / "Applications"
            decoys = [
                apps / "Antigravity (zwe) copy.app",
                apps / "Antigravity (zwe2).app",
            ]
            self.assertEqual(run_cli(["create", "zwe"], env).returncode, 0)
            self.assertTrue((apps / "Antigravity (zwe).app").is_dir())
            for decoy in decoys:
                decoy.mkdir(parents=True)

            self.assertEqual(run_cli(["delete", "zwe", "--force"], env).returncode, 0)
            self.assertFalse((apps / "Antigravity (zwe).app").exists())
            for decoy in decoys:
                self.assertTrue(decoy.is_dir(), f"decoy {decoy.name} must survive")

    def test_launcher_embeds_absolute_interpreter(self):
        if not IS_DARWIN:
            self.skipTest("macOS applets only")
        with sandbox_home() as (home, env):
            self.assertEqual(run_cli(["create", "zwe"], env).returncode, 0)
            scpt = home / "Applications" / "Antigravity (zwe).app" / "Contents" / "Resources" / "Scripts" / "main.scpt"
            data = scpt.read_bytes()
            # AppleScript stores strings as UTF-16BE
            bare = "python3 '".encode("utf-16-be")
            self.assertNotIn(bare, data, "bare python3 breaks under the launchd PATH")
            if sys.executable:
                self.assertIn(sys.executable.encode("utf-16-be"), data)


class ProcessManagementTests(unittest.TestCase):

    def _make_fake_app(self, path: Path, child_pid_file: Path):
        # Mimics the Electron main process: spawns a long-lived child (the
        # "language server") and stays alive itself.
        path.write_text(
            "#!/bin/sh\n"
            f'sleep 300 &\necho "$!" > "{child_pid_file}"\n'
            "sleep 300\n"
        )
        path.chmod(0o755)

    @unittest.skipUnless(IS_DARWIN, "process-group semantics verified on macOS")
    def test_stop_kills_whole_process_group(self):
        with sandbox_home() as (home, env) :
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake = home / "fake-antigravity"
            child_pid_file = home / "child.pid"
            self._make_fake_app(fake, child_pid_file)

            self.assertEqual(run_cli(["create", "grp"], env).returncode, 0)
            launch = run_cli(["launch", "grp", "--app", str(fake)], env)
            self.assertEqual(launch.returncode, 0, launch.stderr)

            self.assertTrue(wait_until(child_pid_file.is_file), "fake app never started")
            main_pid = int((profiles / "grp" / "run.pid").read_text())
            child_pid = int(child_pid_file.read_text())
            self.assertTrue(pid_alive(main_pid))
            self.assertTrue(pid_alive(child_pid))

            stop = run_cli(["stop", "grp"], env)
            self.assertEqual(stop.returncode, 0, stop.stderr)

            self.assertTrue(wait_until(lambda: not pid_alive(main_pid)))
            self.assertTrue(wait_until(lambda: not pid_alive(child_pid)),
                            "language-server child must not be orphaned")

    @unittest.skipUnless(IS_DARWIN, "process-group semantics verified on macOS")
    def test_stop_reaps_children_of_foreground_launch(self):
        """Foreground launches share the caller's process group, so the
        group-kill path can't reach their children — stop must reap them."""
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake = home / "fake-antigravity"
            child_pid_file = home / "child.pid"
            self._make_fake_app(fake, child_pid_file)

            self.assertEqual(run_cli(["create", "fg"], env).returncode, 0)
            launch = subprocess.Popen(
                [sys.executable, str(CLI), "launch", "fg", "--app", str(fake), "-f"],
                env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                self.assertTrue(wait_until(child_pid_file.is_file), "fake app never started")
                child_pid = int(child_pid_file.read_text())
                self.assertTrue(pid_alive(child_pid))

                stop = run_cli(["stop", "fg"], env)
                self.assertEqual(stop.returncode, 0, stop.stderr)
                self.assertTrue(wait_until(lambda: not pid_alive(child_pid)),
                                "foreground launch children must not be orphaned by stop")
            finally:
                launch.terminate()
                launch.wait(timeout=5)

    @unittest.skipUnless(IS_DARWIN, "BSD pgrep specific")
    def test_pgrep_fallback_finds_running_instance_without_pidfile(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake = home / "fake-antigravity"
            fake.write_text("#!/bin/sh\nsleep 300\n")
            fake.chmod(0o755)

            self.assertEqual(run_cli(["create", "grp"], env).returncode, 0)
            self.assertEqual(run_cli(["launch", "grp", "--app", str(fake)], env).returncode, 0)
            try:
                (profiles / "grp" / "run.pid").unlink()

                module = load_cli_module()
                found = module.get_profile_process(
                    profiles / "grp", profiles / "grp" / "data"
                )
                self.assertNotEqual(found, 0, "anchored pgrep fallback must find the process")
            finally:
                result = run_cli(["stop", "grp"], env)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_delete_refuses_while_running(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            if IS_WINDOWS:
                fake = home / "fake-antigravity.cmd"
                fake.write_text("@echo off\nping 127.0.0.1 -n 300 > nul\n")
            else:
                fake = home / "fake-antigravity"
                fake.write_text("#!/bin/sh\nsleep 300\n")
                fake.chmod(0o755)

            self.assertEqual(run_cli(["create", "grp"], env).returncode, 0)
            self.assertEqual(run_cli(["launch", "grp", "--app", str(fake)], env).returncode, 0)
            try:
                result = run_cli(["delete", "grp", "--force"], env)
                self.assertEqual(result.returncode, 1)
                self.assertIn("currently running", result.stderr + result.stdout)
                self.assertTrue((profiles / "grp").exists())
            finally:
                run_cli(["stop", "grp"], env)

    @unittest.skipUnless(IS_DARWIN, "multi-instance process groups verified on macOS")
    def test_multi_instance_concurrency_and_isolation(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake1 = home / "fake-antigravity-1"
            child_pid_1 = home / "child1.pid"
            self._make_fake_app(fake1, child_pid_1)

            fake2 = home / "fake-antigravity-2"
            child_pid_2 = home / "child2.pid"
            self._make_fake_app(fake2, child_pid_2)

            self.assertEqual(run_cli(["create", "prof1"], env).returncode, 0)
            self.assertEqual(run_cli(["create", "prof2"], env).returncode, 0)

            # Launch both instances
            l1 = run_cli(["launch", "prof1", "--app", str(fake1)], env)
            self.assertEqual(l1.returncode, 0, l1.stderr)
            l2 = run_cli(["launch", "prof2", "--app", str(fake2)], env)
            self.assertEqual(l2.returncode, 0, l2.stderr)

            self.assertTrue(wait_until(child_pid_1.is_file))
            self.assertTrue(wait_until(child_pid_2.is_file))

            p1_main = int((profiles / "prof1" / "run.pid").read_text())
            p1_child = int(child_pid_1.read_text())
            p2_main = int((profiles / "prof2" / "run.pid").read_text())
            p2_child = int(child_pid_2.read_text())

            self.assertNotEqual(p1_main, p2_main)
            self.assertTrue(pid_alive(p1_main))
            self.assertTrue(pid_alive(p1_child))
            self.assertTrue(pid_alive(p2_main))
            self.assertTrue(pid_alive(p2_child))

            # list --json should report both running
            listed = run_cli(["list", "--json"], env)
            self.assertEqual(listed.returncode, 0)
            data = json.loads(listed.stdout)
            running_map = {item["name"]: item["running"] for item in data}
            self.assertTrue(running_map.get("prof1"))
            self.assertTrue(running_map.get("prof2"))

            # Duplicate launch of prof1 should detect it is already running
            dup = run_cli(["launch", "prof1", "--app", str(fake1)], env)
            self.assertEqual(dup.returncode, 0)
            self.assertIn("already running", dup.stdout)
            self.assertEqual(int((profiles / "prof1" / "run.pid").read_text()), p1_main)

            # Stopping prof1 must NOT terminate prof2 or prof2's children
            s1 = run_cli(["stop", "prof1"], env)
            self.assertEqual(s1.returncode, 0, s1.stderr)
            self.assertTrue(wait_until(lambda: not pid_alive(p1_main)))
            self.assertTrue(wait_until(lambda: not pid_alive(p1_child)))

            # prof2 must still be fully alive
            self.assertTrue(pid_alive(p2_main), "prof2 must remain alive after stopping prof1")
            self.assertTrue(pid_alive(p2_child), "prof2 child must remain alive after stopping prof1")

            # Clean stop for prof2
            s2 = run_cli(["stop", "prof2"], env)
            self.assertEqual(s2.returncode, 0, s2.stderr)
            self.assertTrue(wait_until(lambda: not pid_alive(p2_main)))
            self.assertTrue(wait_until(lambda: not pid_alive(p2_child)))


class NewFeatureTests(unittest.TestCase):
    """Logs, workspace path, --json, --links and token-expiry features."""

    def _make_echoing_app(self, home: Path) -> Path:
        if IS_WINDOWS:
            fake = home / "fake-antigravity.cmd"
            fake.write_text("@echo off\necho fake-app-started\necho booting-language-server\nping 127.0.0.1 -n 300 > nul\n")
        else:
            fake = home / "fake-antigravity"
            fake.write_text("#!/bin/sh\necho fake-app-started\necho booting-language-server\nsleep 300\n")
            fake.chmod(0o755)
        return fake

    def test_launch_writes_log_and_logs_command_reads_it(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake = self._make_echoing_app(home)
            self.assertEqual(run_cli(["create", "lg"], env).returncode, 0)
            self.assertEqual(run_cli(["launch", "lg", "--app", str(fake)], env).returncode, 0)
            try:
                log_dir = profiles / "lg" / "logs"
                self.assertTrue(wait_until(lambda: log_dir.is_dir() and any(
                    p.stat().st_size > 0 for p in log_dir.glob("launch-*.log"))),
                    "launch must write a non-empty log file")
                result = run_cli(["logs", "lg"], env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("fake-app-started", result.stdout)
                self.assertIn("booting-language-server", result.stdout)
            finally:
                run_cli(["stop", "lg"], env)

    def test_logs_without_launches_is_friendly(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "lg"], env).returncode, 0)
            result = run_cli(["logs", "lg"], env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No logs yet", result.stdout)

    def test_launch_rejects_nonexistent_workspace_path(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            fake = self._make_echoing_app(home)
            self.assertEqual(run_cli(["create", "ws"], env).returncode, 0)
            result = run_cli(["launch", "ws", "--app", str(fake), "/definitely/not/here"], env)
            self.assertEqual(result.returncode, 1, result)
            self.assertIn("does not exist", result.stderr + result.stdout)
            self.assertFalse((profiles / "ws" / "run.pid").exists(), "must not record a pid")

    def test_list_json_is_parseable(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "jz", "-d", "desc"], env).returncode, 0)
            result = run_cli(["list", "--json"], env)
            self.assertEqual(result.returncode, 0, result.stderr)
            items = json.loads(result.stdout)
            item = next(i for i in items if i["name"] == "jz")
            for key in ("running", "pid", "account", "has_token", "token_exp", "token_state", "size", "description"):
                self.assertIn(key, item)
            self.assertEqual(item["description"], "desc")
            self.assertFalse(item["running"])

    def test_info_json_is_parseable(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "jz"], env).returncode, 0)
            result = run_cli(["info", "jz", "--json"], env)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["name"], "jz")
            self.assertIn("directory", data)

    def test_symlink_policy_minimal_and_none(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            (home / ".ssh").mkdir()
            (home / ".config").mkdir()
            (home / "Projects").mkdir()
            # The keychain bridge links from ~/Library/Keychains — create it so
            # "none" has something to keep.
            (home / "Library" / "Keychains").mkdir(parents=True)

            self.assertEqual(run_cli(["create", "nonep", "--links", "none"], env).returncode, 0)
            p_home = profiles / "nonep" / "home"
            self.assertFalse((p_home / ".ssh").exists(), "'none' must not link ~/.ssh")
            self.assertFalse((p_home / "Projects").exists(), "'none' must not link project dirs")
            if IS_DARWIN:
                self.assertTrue((p_home / "Library" / "Keychains").exists(),
                                "keychain bridge must stay for Chromium cookie crypto")

            self.assertEqual(run_cli(["create", "minp", "--links", "minimal"], env).returncode, 0)
            m_home = profiles / "minp" / "home"
            self.assertFalse((m_home / ".ssh").exists(), "'minimal' must not link ~/.ssh")
            self.assertFalse((m_home / ".config").exists(), "'minimal' must not link ~/.config")
            self.assertTrue(is_link_or_junction(m_home / "Projects"), "'minimal' keeps project dirs")

            self.assertEqual(run_cli(["create", "fullp"], env).returncode, 0)
            f_home = profiles / "fullp" / "home"
            self.assertTrue(is_link_or_junction(f_home / ".ssh"), "default policy is 'full'")

    def test_token_expiry_state_classification(self):
        module = load_cli_module()
        self.assertIsNone(module.token_expiry_state(None))
        self.assertIsNone(module.token_expiry_state(""))
        self.assertIsNone(module.token_expiry_state("garbage"))
        now = datetime.now()
        self.assertEqual(module.token_expiry_state((now - timedelta(days=1)).isoformat()), "expired")
        self.assertEqual(module.token_expiry_state((now + timedelta(days=3)).isoformat()), "expiring")
        self.assertEqual(module.token_expiry_state((now + timedelta(days=30)).isoformat()), None)


class PermissionTests(unittest.TestCase):

    @unittest.skipIf(IS_WINDOWS, "POSIX 0700 file modes are not applicable to Windows NTFS")
    def test_profile_dirs_are_owner_only(self):
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "zwe"], env).returncode, 0)
            for d in (profiles, profiles / "zwe", profiles / "zwe" / "data", profiles / "zwe" / "home"):
                mode = d.stat().st_mode & 0o777
                self.assertEqual(mode, 0o700, f"{d} must not be group/world readable")


class ConfigurationInheritanceTests(unittest.TestCase):
    """Tests for profile configuration inheritance (-i) and cloning (--clone-from)."""

    def _setup_host_env(self, home: Path):
        if IS_WINDOWS:
            app_support = home / "AppData" / "Roaming" / "Antigravity" / "User"
        else:
            app_support = home / "Library" / "Application Support" / "Antigravity" / "User"
        app_support.mkdir(parents=True, exist_ok=True)
        (app_support / "settings.json").write_text(json.dumps({"editor.fontSize": 14, "workbench.colorTheme": "Dark"}))
        (app_support / "keybindings.json").write_text(json.dumps([{"key": "cmd+k", "command": "workbench.action.terminal"}]))
        snip_dir = app_support / "snippets"
        snip_dir.mkdir(parents=True, exist_ok=True)
        (snip_dir / "python.json").write_text(json.dumps({"header": {"prefix": "hdr", "body": "#!/usr/bin/env python3"}}))

        gemini = home / ".gemini"
        gemini.mkdir(parents=True, exist_ok=True)
        (gemini / "settings.json").write_text(json.dumps({
            "theme": "Atom One",
            "selectedAuthType": "oauth-personal",
            "jetski-standalone-oauth-token": "SECRET_HOST_TOKEN_DO_NOT_LEAK",
            "google_accounts": [{"email": "host@gmail.com"}],
            "lastLoginUsername": "host@gmail.com",
            "mcpServers": {"pencil": {"command": "pencil-mcp", "env": {"PENCIL_API_KEY": "SECRET_MCP_KEY", "PLAIN_FLAG": "keep-me"}}}
        }))
        (gemini / "jetski-standalone-oauth-token").write_text("RAW_BEARER_TOKEN_HOST")

        gemini_cfg = gemini / "config"
        gemini_cfg.mkdir(parents=True, exist_ok=True)
        (gemini_cfg / "config.json").write_text(json.dumps({
            "userSettings": {
                "artifactReviewMode": "ARTIFACT_REVIEW_MODE_TURBO",
                "remoteControlHostname": "host-machine-private"
            }
        }))
        (gemini_cfg / "mcp_config.json").write_text(json.dumps({
            "mcpServers": {"pencil": {"command": "pencil-mcp", "env": {"PENCIL_API_KEY": "SECRET_MCP_KEY", "PLAIN_FLAG": "keep-me"}}}
        }))

        skills_dir = gemini_cfg / "skills" / "custom-skill"
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / "SKILL.md").write_text("# Custom Skill\nDescription")

    def test_inherit_config_from_host_success(self):
        with sandbox_home() as (home, env):
            self._setup_host_env(home)
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])

            res = run_cli(["create", "work", "-i"], env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("Inherited:", res.stdout)
            self.assertIn("Credentials & session tokens isolated", res.stdout)

            work_dir = profiles / "work"
            # 1. VSCode / Antigravity User settings copied
            self.assertTrue((work_dir / "data" / "User" / "settings.json").is_file())
            self.assertTrue((work_dir / "data" / "User" / "keybindings.json").is_file())
            self.assertTrue((work_dir / "data" / "User" / "snippets" / "python.json").is_file())

            # 2. Antigravity settings sanitized (tokens removed)
            gemini_s = work_dir / "home" / ".gemini" / "settings.json"
            self.assertTrue(gemini_s.is_file())
            data = json.loads(gemini_s.read_text())
            self.assertEqual(data.get("theme"), "Atom One")
            self.assertNotIn("jetski-standalone-oauth-token", data)
            self.assertNotIn("google_accounts", data)
            self.assertNotIn("lastLoginUsername", data)

            # 3. Raw token file MUST NOT exist
            self.assertFalse((work_dir / "home" / ".gemini" / "jetski-standalone-oauth-token").exists())

            # 4. config.json sanitized
            cfg = json.loads((work_dir / "home" / ".gemini" / "config" / "config.json").read_text())
            self.assertEqual(cfg["userSettings"]["artifactReviewMode"], "ARTIFACT_REVIEW_MODE_TURBO")
            self.assertNotIn("remoteControlHostname", cfg["userSettings"])

            # 5. MCP tool configs inherited
            self.assertTrue((work_dir / "home" / ".gemini" / "config" / "mcp_config.json").is_file())

            # 6. Skills symlinked
            skills = work_dir / "home" / ".gemini" / "config" / "skills"
            self.assertTrue(is_link_or_junction(skills))
            self.assertTrue((skills / "custom-skill" / "SKILL.md").is_file())

            # 7. Metadata and info inspection
            meta = json.loads((work_dir / "profile.json").read_text())
            self.assertEqual(meta.get("inherited_from"), "host")

            info = run_cli(["info", "work", "--json"], env)
            self.assertEqual(info.returncode, 0)
            self.assertEqual(json.loads(info.stdout).get("inherited_from"), "host")

    def test_clone_from_existing_profile(self):
        with sandbox_home() as (home, env):
            self._setup_host_env(home)
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])

            # Create source profile and customize it
            self.assertEqual(run_cli(["create", "src_prof", "-i"], env).returncode, 0)
            src_user = profiles / "src_prof" / "data" / "User"
            (src_user / "settings.json").write_text(json.dumps({"editor.fontSize": 18}))
            (src_user / "snippets" / "python.json").write_text(json.dumps({"body": "custom-snippet-v1"}))
            # Put a fake token inside src_prof to verify it is NOT cloned
            (profiles / "src_prof" / "home" / ".gemini" / "jetski-standalone-oauth-token").write_text("SRC_TOKEN")

            # Clone to clone_prof
            res = run_cli(["create", "clone_prof", "--clone-from", "src_prof"], env)
            self.assertEqual(res.returncode, 0, res.stderr)

            clone_dir = profiles / "clone_prof"
            self.assertTrue((clone_dir / "data" / "User" / "settings.json").is_file())
            clone_settings = json.loads((clone_dir / "data" / "User" / "settings.json").read_text())
            self.assertEqual(clone_settings.get("editor.fontSize"), 18)

            # Verify deep copy isolation: editing clone does not modify source
            (clone_dir / "data" / "User" / "snippets" / "python.json").write_text(json.dumps({"body": "clone-snippet-modified"}))
            src_snip = json.loads((src_user / "snippets" / "python.json").read_text())
            self.assertEqual(src_snip.get("body"), "custom-snippet-v1", "source profile snippet must remain unchanged")

            # Verify credentials are NOT cloned
            self.assertFalse((clone_dir / "home" / ".gemini" / "jetski-standalone-oauth-token").exists())

            # Verify profile metadata
            meta = json.loads((clone_dir / "profile.json").read_text())
            self.assertEqual(meta.get("inherited_from"), "src_prof")

    def test_mutual_exclusion_inherit_and_clone(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "p1"], env).returncode, 0)
            res = run_cli(["create", "p2", "-i", "--clone-from", "p1"], env)
            self.assertEqual(res.returncode, 1)
            self.assertIn("Cannot specify both --inherit-config and --clone-from", res.stderr + res.stdout)

    def test_clone_from_nonexistent_and_self(self):
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "p1"], env).returncode, 0)
            res_self = run_cli(["create", "p1", "--clone-from", "p1"], env)
            # Fails either because profile already exists or cannot clone from itself
            self.assertNotEqual(res_self.returncode, 0)

            res_self2 = run_cli(["create", "new_p", "--clone-from", "new_p"], env)
            self.assertEqual(res_self2.returncode, 1)
            self.assertIn("Cannot clone a profile from itself", res_self2.stderr + res_self2.stdout)

            res_ghost = run_cli(["create", "new_p2", "--clone-from", "ghost_prof"], env)
            self.assertEqual(res_ghost.returncode, 1)
            self.assertIn("does not exist", res_ghost.stderr + res_ghost.stdout)

    def test_mcp_secret_values_stripped(self):
        """MCP env/headers secrets must not ride along into a clone — the
        'credentials never copied' guarantee has to reach inside mcpServers."""
        with sandbox_home() as (home, env):
            self._setup_host_env(home)
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "mcp_prof", "-i"], env).returncode, 0)

            mcp_cfg = json.loads((profiles / "mcp_prof" / "home" / ".gemini" / "config" / "mcp_config.json").read_text())
            env_map = mcp_cfg["mcpServers"]["pencil"]["env"]
            self.assertEqual(env_map.get("PENCIL_API_KEY"), "", "MCP secret env must be stripped")
            self.assertEqual(env_map.get("PLAIN_FLAG"), "keep-me", "non-secret env must be preserved")

            gemini_s = json.loads((profiles / "mcp_prof" / "home" / ".gemini" / "settings.json").read_text())
            s_env = gemini_s["mcpServers"]["pencil"]["env"]
            self.assertEqual(s_env.get("PENCIL_API_KEY"), "")

    def test_no_mcp_flag(self):
        with sandbox_home() as (home, env):
            self._setup_host_env(home)
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])

            res = run_cli(["create", "nomcp_prof", "-i", "--no-mcp"], env)
            self.assertEqual(res.returncode, 0, res.stderr)

            nomcp_dir = profiles / "nomcp_prof"
            self.assertFalse((nomcp_dir / "home" / ".gemini" / "config" / "mcp_config.json").exists())
            gemini_s = json.loads((nomcp_dir / "home" / ".gemini" / "settings.json").read_text())
            self.assertNotIn("mcpServers", gemini_s)

    def test_security_symlink_attack_rejection(self):
        if IS_WINDOWS:
            self.skipTest("Symlink attack testing requires elevation or Developer Mode on Windows")
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            canary = home / "secret_host_canary.txt"
            canary.write_text("CONFIDENTIAL_SYSTEM_DATA")

            self.assertEqual(run_cli(["create", "src_evil"], env).returncode, 0)
            # Attacker creates a malicious symlink inside source profile pointing outside
            src_user = profiles / "src_evil" / "data" / "User"
            src_user.mkdir(parents=True, exist_ok=True)
            evil_link = src_user / "settings.json"
            evil_link.symlink_to(canary)

            res = run_cli(["create", "victim_clone", "--clone-from", "src_evil"], env)
            self.assertEqual(res.returncode, 0)

            victim_settings = profiles / "victim_clone" / "data" / "User" / "settings.json"
            self.assertFalse(victim_settings.exists(), "malicious symlink must NOT be copied")

    def test_clone_rejects_path_traversal_source_name(self):
        with sandbox_home() as (_, env):
            for bad_source in ("..", ".", "../etc", "a/b", "`touch`"):
                with self.subTest(source=bad_source):
                    res = run_cli(["create", "victim", "--clone-from", bad_source], env)
                    self.assertEqual(res.returncode, 1)


class WebConsoleTests(unittest.TestCase):
    """Unit tests for the Web Console & Widget Server."""

    def test_web_help_command(self):
        with sandbox_home() as (_, env):
            res = run_cli(["web", "--help"], env)
            self.assertEqual(res.returncode, 0)
            self.assertIn("--port", res.stdout)
            self.assertIn("--widget", res.stdout)
            self.assertIn("--no-browser", res.stdout)

    def test_web_server_endpoints(self):
        import urllib.request
        import threading

        with sandbox_home() as (home, env):
            self.assertEqual(run_cli(["create", "webtest"], env).returncode, 0)

            # Ensure current process env has PARAGRAVITY_PROFILES_DIR
            old_profiles_dir = os.environ.get("PARAGRAVITY_PROFILES_DIR")
            os.environ["PARAGRAVITY_PROFILES_DIR"] = env["PARAGRAVITY_PROFILES_DIR"]

            # Import and start web_server on an ephemeral port
            sys.path.insert(0, str(REPO_ROOT / "bin"))
            import web_server

            server_address = ("127.0.0.1", 0)  # Bind ephemeral free port
            httpd = web_server.ThreadingHTTPServer(server_address, web_server.ParaGravityHandler)
            port = httpd.server_port

            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()

            try:
                base_url = f"http://127.0.0.1:{port}"

                # 1. System API
                with urllib.request.urlopen(f"{base_url}/api/system", timeout=3) as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode())
                    self.assertIn("version", data)
                    self.assertIn("platform", data)

                # 2. Profiles API
                with urllib.request.urlopen(f"{base_url}/api/profiles", timeout=3) as resp:
                    self.assertEqual(resp.status, 200)
                    profiles = json.loads(resp.read().decode())
                    names = [p["name"] for p in profiles]
                    self.assertIn("webtest", names)

                # 3. Widget endpoint
                with urllib.request.urlopen(f"{base_url}/widget", timeout=3) as resp:
                    self.assertEqual(resp.status, 200)
                    html = resp.read().decode()
                    self.assertIn("ParaGravity 悬浮挂件 HUD", html)

                # 4. Fallback / Main console endpoint
                with urllib.request.urlopen(f"{base_url}/", timeout=3) as resp:
                    self.assertEqual(resp.status, 200)
                    html = resp.read().decode()
                    self.assertIn("ParaGravity", html)

                # 5. Cross-origin rejection check
                req = urllib.request.Request(
                    f"{base_url}/api/batch/launch",
                    data=json.dumps({"names": []}).encode(),
                    headers={"Origin": "http://evil-attacker.com", "Content-Type": "application/json"},
                    method="POST"
                )
                try:
                    urllib.request.urlopen(req, timeout=3)
                    self.fail("Cross-origin request from untrusted origin must be rejected")
                except urllib.error.HTTPError as e:
                    self.assertEqual(e.code, 403)

            finally:
                httpd.shutdown()
                httpd.server_close()
                if old_profiles_dir is not None:
                    os.environ["PARAGRAVITY_PROFILES_DIR"] = old_profiles_dir
                else:
                    os.environ.pop("PARAGRAVITY_PROFILES_DIR", None)

    def test_static_traversal_blocked(self):
        """`/..` and `%2e%2e` must never escape dashboard/dist (LFI fix)."""
        import socket
        import threading
        import urllib.error
        import urllib.request

        sys.path.insert(0, str(REPO_ROOT / "bin"))
        import web_server

        with tempfile.TemporaryDirectory(prefix="pgrav-dist-") as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<html>ok</html>")
            (root / "secret.txt").write_text("SECRET-LEAK")

            old_dist = web_server.DASHBOARD_DIST
            web_server.DASHBOARD_DIST = dist
            httpd = web_server.ThreadingHTTPServer(("127.0.0.1", 0), web_server.ParaGravityHandler)
            port = httpd.server_port
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                # urllib normalizes dot-segments, so drive the raw socket for
                # the literal `/../` probe — exactly what curl --path-as-is sends.
                s = socket.create_connection(("127.0.0.1", port), timeout=3)
                s.sendall(b"GET /../secret.txt HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
                raw = s.recv(8192).decode("utf-8", "replace")
                s.close()
                self.assertNotIn("SECRET-LEAK", raw, "traversal must not serve files outside dist")
                self.assertIn("403", raw.split("\r\n")[0])

                # Percent-encoded traversal must also be rejected.
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/%2e%2e/secret.txt", timeout=3)
                    self.fail("percent-encoded traversal must be rejected")
                except urllib.error.HTTPError as e:
                    self.assertEqual(e.code, 403)

                # GET APIs now honour the same origin policy as POST/DELETE.
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    headers={"Origin": "http://evil-attacker.com"},
                )
                try:
                    urllib.request.urlopen(req, timeout=3)
                    self.fail("cross-origin GET must be rejected")
                except urllib.error.HTTPError as e:
                    self.assertEqual(e.code, 403)
            finally:
                httpd.shutdown()
                httpd.server_close()
                web_server.DASHBOARD_DIST = old_dist


class RegressionHardeningTests(unittest.TestCase):
    """Locks in the hardening fixes: JSON purity, argv handling, pid reuse."""

    def test_list_json_empty_emits_json_array(self):
        with sandbox_home() as (home, env):
            # profiles dir does not exist at all
            res = run_cli(["list", "--json"], env)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(json.loads(res.stdout), [])

            # exists but empty
            Path(env["PARAGRAVITY_PROFILES_DIR"]).mkdir(parents=True)
            res = run_cli(["list", "--json"], env)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(json.loads(res.stdout), [])

    def test_extra_positional_rejected_on_non_path_commands(self):
        """The Python<3.10 path fallback must not swallow garbage args."""
        with sandbox_home() as (_, env):
            self.assertEqual(run_cli(["create", "victim"], env).returncode, 0)
            for argv in (["delete", "victim", "oops"], ["stop", "victim", "typo"]):
                with self.subTest(argv=argv):
                    res = run_cli(argv, env)
                    self.assertEqual(res.returncode, 2)
                    self.assertIn("unrecognized arguments", res.stderr)
            self.assertTrue(
                (Path(env["PARAGRAVITY_PROFILES_DIR"]) / "victim").exists(),
                "rejected command must not have side effects",
            )

    def test_logs_lines_zero_prints_nothing(self):
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "lg"], env).returncode, 0)
            log_dir = profiles / "lg" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "launch-1.log").write_text("line-a\nline-b\n")

            res = run_cli(["logs", "lg", "-n", "0"], env)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout, "")
            res = run_cli(["logs", "lg", "-n", "1"], env)
            self.assertEqual(res.stdout.strip(), "line-b")

    @unittest.skipUnless(not IS_WINDOWS, "POSIX ps/pid semantics")
    def test_stale_pidfile_recycled_pid_is_not_trusted(self):
        """A run.pid pointing at a recycled, unrelated pid must not make the
        profile look 'running' — and must never be a kill target."""
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "zp"], env).returncode, 0)

            sleeper = subprocess.Popen(["sleep", "30"])
            try:
                pid_file = profiles / "zp" / "run.pid"
                pid_file.write_text(str(sleeper.pid))
                module = load_cli_module()
                self.assertEqual(
                    module.get_profile_process(profiles / "zp", profiles / "zp" / "data"),
                    0, "recycled pid must not be treated as the profile process")
                self.assertFalse(pid_file.exists(), "stale pid file must be removed")
            finally:
                sleeper.terminate()
                sleeper.wait()


if __name__ == "__main__":
    unittest.main()
