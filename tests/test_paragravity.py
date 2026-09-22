"""Stdlib-only test suite for the `bin/paragravity` CLI.

Every test runs the real CLI in a sandboxed $HOME (via PARAGRAVITY_PROFILES_DIR
and HOME overrides), so nothing here touches the developer's real profiles or
~/Applications.
"""

import contextlib
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "bin" / "paragravity"
IS_DARWIN = sys.platform == "darwin"

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
    try:
        os.kill(pid, 0)
        return True
    except OSError:
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
        env["PARAGRAVITY_PROFILES_DIR"] = str(home / ".antigravity-profiles")
        yield home, env


def run_cli(args, env, stdin=subprocess.DEVNULL):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env, stdin=stdin, capture_output=True, text=True, timeout=120,
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
                        self.assertIn("Invalid profile name", result.stdout)
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
            self.assertIn("zwe", listed.stdout)

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
            fake = home / "fake-antigravity"
            fake.write_text("#!/bin/sh\nsleep 300\n")
            fake.chmod(0o755)

            self.assertEqual(run_cli(["create", "grp"], env).returncode, 0)
            self.assertEqual(run_cli(["launch", "grp", "--app", str(fake)], env).returncode, 0)
            try:
                result = run_cli(["delete", "grp", "--force"], env)
                self.assertEqual(result.returncode, 1)
                self.assertIn("currently running", result.stdout)
                self.assertTrue((profiles / "grp").exists())
            finally:
                run_cli(["stop", "grp"], env)


class PermissionTests(unittest.TestCase):

    def test_profile_dirs_are_owner_only(self):
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "zwe"], env).returncode, 0)
            for d in (profiles, profiles / "zwe", profiles / "zwe" / "data", profiles / "zwe" / "home"):
                mode = d.stat().st_mode & 0o777
                self.assertEqual(mode, 0o700, f"{d} must not be group/world readable")


if __name__ == "__main__":
    unittest.main()
