# 🤖 ParaGravity Agent Directive (`AGENT.md`)

> **Machine-readable setup and operation guide for AI coding agents (Claude Code, Cursor, Antigravity, Windsurf, Aider).**

This document provides deterministic instructions for an AI agent to install, configure, and manage **ParaGravity** on behalf of a developer.

---

## 1. Goal
Configure native, isolated multi-account sandboxes for Google Antigravity so the user can run multiple Gemini Pro accounts simultaneously without quota bottlenecks.

---

## 2. Environment Verification

1. **Check OS**:
   - macOS: Verify `python3` is available.
   - Windows: Verify `python` (3.8+) and PowerShell / CMD / Git Bash.
2. **Check Antigravity Installation**:
   - macOS: `/Applications/Antigravity.app` or `~/Applications/Antigravity.app`
   - Windows: `%LOCALAPPDATA%\Programs\Antigravity`

---

## 3. Installation Step

### macOS / Linux:
Run the official non-invasive installer:
```bash
curl -fsSL https://raw.githubusercontent.com/edison-land/paragravity/main/install.sh | bash
```
Ensure `~/.local/bin` is in `$PATH` (or reload shell).

### Windows (PowerShell):
```powershell
git clone https://github.com/edison-land/paragravity.git $HOME\.paragravity
# Add $HOME\.paragravity\bin to PATH, or invoke directly via $HOME\.paragravity\bin\pgrav.cmd
```

---

## 4. Provisioning Profiles

To create a new profile named `<profile_name>`:

### Recommended: Inherit Host Configs (Zero Blank Canvas)
```bash
pgrav create <profile_name> -i
```
*Note: `-i` copies editor settings, snippets, skills, and links MCP tools. It strictly excludes OAuth tokens and credentials.*

### Strictest Security Isolation (Minimal Symlinks)
If the user wants to shield host `~/.ssh` or `~/.config` from agents in the profile:
```bash
pgrav create <profile_name> --links minimal
```

---

## 5. Verification Commands

1. **List all profiles and process status**:
   ```bash
   pgrav list
   ```
2. **Launch a profile**:
   ```bash
   pgrav launch <profile_name> [optional_project_path]
   ```
3. **Inspect profile metadata**:
   ```bash
   pgrav info <profile_name> --json
   ```

---

## 6. Completion Report to User
Once installed:
- Notify the user that profile `<profile_name>` is provisioned.
- Inform macOS users they can launch it directly with **Spotlight (`Cmd + Space`)** by typing `Antigravity (<profile_name>)`.
- Provide `pgrav list` output to show the current active profiles.
