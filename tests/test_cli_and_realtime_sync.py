"""Tests for Antigravity 2.0 JSON OAuth detection, `agy` CLI profile switching,
and two-tier real-time data synchronization across host and profiles.
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
IS_WINDOWS = sys.platform == "win32"


def load_cli_module():
    loader = importlib.machinery.SourceFileLoader("paragravity_cli_v13", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


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


@contextlib.contextmanager
def sandbox_home():
    with tempfile.TemporaryDirectory(prefix="pgrav-v13-test-") as tmp:
        home = Path(tmp)
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
        env["APPDATA"] = str(home / "AppData" / "Roaming")
        env["PARAGRAVITY_PROFILES_DIR"] = str(home / ".antigravity-profiles")
        env["PARAGRAVITY_REAL_HOME"] = str(home)
        env["PARAGRAVITY_NO_DAEMON"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        yield home, env


def run_cli(args, env, stdin=subprocess.DEVNULL):
    return subprocess.run(
        [sys.executable, "-W", "error::FutureWarning", str(CLI), *args],
        env=env,
        stdin=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


class CliAndRealtimeSyncTests(unittest.TestCase):
    def test_json_oauth_token_account_detection_no_warnings(self):
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "alpha"], env).returncode, 0)

            tok_path = profiles / "alpha" / "home" / ".gemini" / "jetski-standalone-oauth-token"
            tok_path.parent.mkdir(parents=True, exist_ok=True)
            past_exp = (datetime.now() - timedelta(hours=5)).isoformat()
            tok_payload = {
                "token": {
                    "access_token": "ya29.fake/access+token.with/slashes",
                    "token_type": "Bearer",
                    "refresh_token": "1//0fake-refresh-token",
                    "expiry": past_exp,
                },
                "auth_method": "consumer",
                "id_token_email": "alpha.dev@gmail.com",
            }
            tok_path.write_text(json.dumps(tok_payload), encoding="utf-8")

            res_json = run_cli(["list", "--json"], env)
            self.assertEqual(res_json.returncode, 0, res_json.stderr)
            self.assertEqual(res_json.stderr, "")
            items = json.loads(res_json.stdout)
            alpha = next(item for item in items if item["name"] == "alpha")
            self.assertEqual(alpha["account"], "alpha.dev@gmail.com")
            self.assertTrue(alpha["has_token"])
            self.assertIsNone(alpha["token_state"])

            res_human = run_cli(["list"], env)
            self.assertEqual(res_human.returncode, 0, res_human.stderr)
            self.assertIn("alpha.dev@gmail.com", res_human.stdout)
            self.assertNotIn("token expired", res_human.stdout)

    def test_desktop_cli_oauth_token_bridge(self):
        with sandbox_home() as (_, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "beta"], env).returncode, 0)

            pdir = profiles / "beta"
            gui_tok = pdir / "home" / ".gemini" / "jetski-standalone-oauth-token"
            cli_tok = pdir / "home" / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
            gui_tok.parent.mkdir(parents=True, exist_ok=True)

            payload_v1 = {
                "token": {"access_token": "tok-v1", "refresh_token": "ref-v1"},
                "id_token_email": "beta.user@gmail.com",
            }
            gui_tok.write_text(json.dumps(payload_v1), encoding="utf-8")

            module = load_cli_module()
            self.assertTrue(module.sync_profile_auth_tokens(pdir))
            self.assertTrue(cli_tok.is_file())
            self.assertEqual(json.loads(cli_tok.read_text(encoding="utf-8")), payload_v1)

            # Newer CLI login/refresh syncs back to GUI token
            payload_v2 = {
                "token": {"access_token": "tok-v2", "refresh_token": "ref-v2"},
                "id_token_email": "beta.user@gmail.com",
            }
            cli_tok.write_text(json.dumps(payload_v2), encoding="utf-8")
            newer_ns = time.time_ns() + 5_000_000_000
            os.utime(cli_tok, ns=(newer_ns, newer_ns))

            self.assertTrue(module.sync_profile_auth_tokens(pdir))
            self.assertEqual(json.loads(gui_tok.read_text(encoding="utf-8")), payload_v2)

    def test_agy_cli_use_current_and_shim_dispatch(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            self.assertEqual(run_cli(["create", "alpha"], env).returncode, 0)

            helper_py = home / "mock_agy.py"
            helper_py.write_text(
                "import json, os, sys\n"
                "print(json.dumps({\n"
                "  'HOME': os.environ.get('HOME'),\n"
                "  'SSH_CONNECTION': os.environ.get('SSH_CONNECTION'),\n"
                "  'ARGS': sys.argv[1:]\n"
                "}))\n",
                encoding="utf-8",
            )
            if IS_WINDOWS:
                mock_agy = home / "mock_agy.cmd"
                mock_agy.write_text(f'@echo off\r\n"{sys.executable}" "{helper_py}" %*\r\n', encoding="utf-8")
            else:
                mock_agy = home / "mock_agy"
                mock_agy.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{helper_py}" "$@"\n', encoding="utf-8")
                mock_agy.chmod(0o755)
            env["ANTIGRAVITY_CLI_BIN"] = str(mock_agy)

            use_alpha = run_cli(["use", "alpha"], env)
            self.assertEqual(use_alpha.returncode, 0, use_alpha.stderr)

            cur = run_cli(["current", "--json"], env)
            self.assertEqual(cur.returncode, 0, cur.stderr)
            cur_data = json.loads(cur.stdout)
            self.assertEqual(cur_data["active_profile"], "alpha")
            self.assertTrue(cur_data["shim_installed"])

            cli_alpha = run_cli(["cli", "models", "--flag"], env)
            self.assertEqual(cli_alpha.returncode, 0, cli_alpha.stderr)
            out_alpha = json.loads(cli_alpha.stdout)
            self.assertEqual(Path(out_alpha["HOME"]).resolve(), (profiles / "alpha" / "home").resolve())
            self.assertTrue(out_alpha["SSH_CONNECTION"])
            self.assertEqual(out_alpha["ARGS"], ["models", "--flag"])

            use_host = run_cli(["use", "host"], env)
            self.assertEqual(use_host.returncode, 0, use_host.stderr)

            cli_host = run_cli(["cli", "models"], env)
            self.assertEqual(cli_host.returncode, 0, cli_host.stderr)
            out_host = json.loads(cli_host.stdout)
            self.assertEqual(Path(out_host["HOME"]).resolve(), home.resolve())
            self.assertIsNone(out_host["SSH_CONNECTION"])

    def test_two_tier_realtime_sync(self):
        with sandbox_home() as (home, env):
            profiles = Path(env["PARAGRAVITY_PROFILES_DIR"])
            host_gemini = home / ".gemini"
            host_cfg = host_gemini / "config"
            (host_cfg / "projects").mkdir(parents=True)
            (host_cfg / "skills" / "host-skill").mkdir(parents=True)
            (host_cfg / "plugins" / "pstack").mkdir(parents=True)
            (host_gemini / "antigravity-cli").mkdir(parents=True)

            (host_cfg / "projects" / "proj-host.json").write_text(
                json.dumps({"id": "proj-host", "name": "my-project"}), encoding="utf-8"
            )
            (host_cfg / "projects" / "swarm-host.json").write_text(
                json.dumps({"id": "swarm-host-id", "name": "swarm/swarm_board"}), encoding="utf-8"
            )
            (host_cfg / "skills" / "host-skill" / "SKILL.md").write_text("# Host Skill", encoding="utf-8")
            (host_cfg / "plugins" / "pstack" / "plugin.json").write_text("{}", encoding="utf-8")
            (host_cfg / "hooks.json").write_text(json.dumps({"herdr": {}}), encoding="utf-8")
            (host_gemini / "antigravity-cli" / "settings.json").write_text(
                json.dumps({"model": "Orchestrator (Carbon)"}), encoding="utf-8"
            )
            (host_cfg / "config.json").write_text(
                json.dumps({
                    "plugins": {"pstack": {"enabled": True}},
                    "sidecars": {"swarm/swarm_board": {"projectId": "swarm-host-id"}},
                    "userSettings": {
                        "themeMode": "THEME_MODE_DARK",
                        "remoteControlHostname": "host-box",
                        "remoteControlEnabled": True,
                    },
                }),
                encoding="utf-8",
            )

            self.assertEqual(run_cli(["create", "p1"], env).returncode, 0)
            self.assertEqual(run_cli(["create", "p2"], env).returncode, 0)

            # Simulate p1 previously having its own plugin, duplicate swarm project, and hostname
            p1_cfg = profiles / "p1" / "home" / ".gemini" / "config"
            # Replace links temporarily to simulate pre-existing divergent profile state before sync
            for sub in ("projects", "plugins"):
                target = p1_cfg / sub
                if IS_WINDOWS and is_link_or_junction(target):
                    os.rmdir(target)
                elif target.is_symlink():
                    target.unlink()
                elif target.is_dir():
                    target.rmdir()
            (p1_cfg / "projects").mkdir(parents=True)
            (p1_cfg / "projects" / "swarm-p1.json").write_text(
                json.dumps({"id": "swarm-p1-id", "name": "swarm/swarm_board"}), encoding="utf-8"
            )
            (p1_cfg / "plugins" / "gemini-api").mkdir(parents=True)
            (p1_cfg / "plugins" / "gemini-api" / "plugin.json").write_text("{}", encoding="utf-8")
            (p1_cfg / "config.json").write_text(
                json.dumps({
                    "plugins": {"gemini-api": {"installedFrom": {"version": "2.7.0"}}},
                    "sidecars": {"swarm/swarm_board": {"projectId": "swarm-p1-id"}},
                    "userSettings": {"remoteControlHostname": "p1-box"},
                }),
                encoding="utf-8",
            )
            (profiles / ".sync_state.json").unlink(missing_ok=True)

            sync_res = run_cli(["sync", "now", "--once"], env)
            self.assertEqual(sync_res.returncode, 0, sync_res.stderr)

            for pname in ("p1", "p2"):
                pcfg = profiles / pname / "home" / ".gemini" / "config"
                for sub in ("projects", "skills", "plugins"):
                    self.assertTrue(is_link_or_junction(pcfg / sub), f"{pname} {sub} must be linked")
                self.assertTrue((pcfg / "projects" / "proj-host.json").is_file())
                self.assertTrue((pcfg / "plugins" / "pstack" / "plugin.json").is_file())
                self.assertTrue((pcfg / "plugins" / "gemini-api" / "plugin.json").is_file())
                self.assertTrue((pcfg / "hooks.json").is_file())
                self.assertTrue((profiles / pname / "home" / ".gemini" / "antigravity-cli" / "settings.json").is_file())

            # Duplicate swarm/swarm_board file must not be copied into host
            swarm_files = [
                p for p in (host_cfg / "projects").glob("*.json")
                if json.loads(p.read_text(encoding="utf-8")).get("name") == "swarm/swarm_board"
            ]
            self.assertEqual(len(swarm_files), 1)

            # Check config.json union-merge + distinct remoteControlHostname preservation
            host_c = json.loads((host_cfg / "config.json").read_text(encoding="utf-8"))
            p1_c = json.loads((p1_cfg / "config.json").read_text(encoding="utf-8"))
            self.assertIn("pstack", host_c["plugins"])
            self.assertIn("gemini-api", host_c["plugins"])
            self.assertIn("pstack", p1_c["plugins"])
            self.assertIn("gemini-api", p1_c["plugins"])
            self.assertEqual(host_c["userSettings"].get("remoteControlHostname"), "host-box")
            self.assertTrue(host_c["userSettings"].get("remoteControlEnabled"))
            self.assertEqual(p1_c["userSettings"].get("remoteControlHostname"), "p1-box")
            self.assertNotIn("remoteControlEnabled", p1_c["userSettings"])

            # Live creation inside p1 skill dir appears immediately in host and p2
            new_skill = p1_cfg / "skills" / "live-skill"
            new_skill.mkdir()
            (new_skill / "SKILL.md").write_text("# Live", encoding="utf-8")
            self.assertTrue((host_cfg / "skills" / "live-skill" / "SKILL.md").is_file())
            self.assertTrue((profiles / "p2" / "home" / ".gemini" / "config" / "skills" / "live-skill" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
