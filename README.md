# 🌌 ParaGravity (`pgrav`)

> **Native, non-invasive parallel multi-account & sandbox manager for Google Antigravity.**  
> Run multiple Google Gemini Pro accounts side-by-side in independent, isolated windows on macOS and Windows.

English | [简体中文](README_zh.md) | [Website / Docs](https://edison-land.github.io/paragravity)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS | Windows](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)]()
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-yellow.svg)]()
[![Follow on X](https://img.shields.io/badge/X-@Edison__aware-black?logo=x)](https://x.com/Edison_aware)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

---

## ✨ Key Advantages

- 🚀 **True Parallel Concurrency**: Run multiple Google Gemini Pro accounts side-by-side in separate windows simultaneously without restarting or session switching.
- 🛡️ **100% Non-Invasive**: Built strictly on Chromium/Electron's official `--user-data-dir` sandboxing. Zero binary patching, zero internal database modifications, zero account security risks.
- 🔑 **Native Google OAuth**: Complete, untouched Google Cloud authentication flow. Token refresh and sign-in redirects work seamlessly without proxies or interruptions.
- 🔍 **Native Desktop Integration**: Automatically generates independent macOS `.app` bundles (indexed by Spotlight) or Windows Desktop & Start Menu shortcuts (`.lnk`). Launch your instances directly via **Spotlight (`Cmd + Space`)** or **Windows Search (`Win + S`)**.
- ⚡ **Zero-Footprint & Ultra-Lightweight**: No background daemon eating RAM (0 MB idle overhead). Powered purely by Python 3 with zero external pip or npm dependencies.
- 🗂️ **Total Workspace Isolation**: Each instance maintains completely separated extensions, local storage, indexedDB, and chat histories, preventing workspace contamination.

---

## 🚀 Quick Start

### 1. macOS One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/edison-land/paragravity/main/install.sh | bash
```

### 2. Windows Quick Start (PowerShell / CMD)

Clone the repository and add the `bin` directory to your user `PATH`:

```powershell
git clone https://github.com/edison-land/paragravity.git $HOME\.paragravity
# Add $HOME\.paragravity\bin to PATH, then use:
pgrav create work
```

> 💡 **Windows notes**
> - Open a **new terminal** after updating `PATH` — already-open shells won't pick up the change.
> - `python` must be on `PATH` (any Python 3.8+ install works).
> - **Git Bash (MSYS2) is fully supported.** `bin/pgrav` is a real POSIX script rather than a symlink, so it survives clones made with Windows' default `core.symlinks=false` and forwards arguments correctly. In CMD/PowerShell the bundled `pgrav.cmd` is used automatically.

### 3. Homebrew Tap (Coming Soon)

```bash
brew tap edison-land/tap
brew install paragravity
```

---

## 📖 CLI Usage

> 💡 **Tip**: Both `pgrav` (short) and `paragravity` (full) are registered and ready to use!

### 1. Create an Isolated Profile
Create a new sandbox with a single command:
```bash
pgrav create zwe
```
This instantly:
- Provisions an isolated sandbox at `~/.antigravity-profiles/zwe`
- Generates a native macOS application `Antigravity (zwe).app` in `~/Applications`
- Lives in `~/Applications`, which Spotlight indexes automatically — find it with **Spotlight (`Cmd + Space`)**

To launch immediately upon creation:
```bash
pgrav create work --launch
```

To keep real `~/.ssh` / `~/.config` out of reach of agents running inside the profile, tighten the symlink policy with `--links` (default `full` preserves the original behavior):
```bash
pgrav create work --links minimal   # link git/shell configs and project dirs, skip .ssh/.config
pgrav create work --links none      # link almost nothing (keychain bridge only)
```

#### Inherit or Clone Configuration (No More Blank Canvas!)
New profiles start clean, but you often want your custom keybindings, editor settings, snippets, agent skills, or MCP tools without having to re-configure them.

- **Inherit from host**: Copy settings and snippets, link skills & MCP tools from your host environment:
  ```bash
  pgrav create work -i
  # or
  pgrav create work --inherit-config
  ```
- **Clone from an existing profile**: Deep-copy configurations from another profile into a self-contained clone (independent lifecycle):
  ```bash
  pgrav create work2 --clone-from work
  ```
- **Exclude MCP tools**: Skip MCP tools inheritance if you prefer a clean tool slate:
  ```bash
  pgrav create work -i --no-mcp
  ```

> 🔒 **Security Guarantee**: Strict credential and session isolation. OAuth tokens (`jetski-standalone-oauth-token`, `oauth_creds.json`), Google account IDs, cookies, local storage, and conversation histories are **NEVER** copied or inherited. All profiles are created with owner-only (`0700`/`0600`) permissions.

### 2. List All Profiles & Status
View all your parallel instances, live process status, and bound Google accounts:
```bash
pgrav list
# or simply:
pgrav ls
```

> 💡 Computing on-disk size walks every file in the profile, which is slow once profiles grow — so it is off by default. Use `pgrav list --size` when you need it, or `pgrav list --json` for machine-readable output in scripts/CI.

**Example Output:**
```text
PROFILE            STATUS         PID      ACCOUNT (GOOGLE)               SIZE       DESCRIPTION
───────────────────────────────────────────────────────────────────────────────────────────────
zwe                ● Running      49377    zwe.dev@gmail.com              —          Development account
work               ○ Stopped      -        work@company.com               —          Company projects
```

### 3. Launch an Instance
```bash
pgrav launch zwe
```
*Or simply press `Cmd + Space` anywhere on your Mac and type `Antigravity (zwe)`!*

You can also open a project folder directly at launch:
```bash
pgrav launch zwe ~/Projects/demo
```

### 4. Stop a Running Instance
```bash
pgrav stop zwe
```
Stopping is staged: the Electron main process first gets a chance to shut down cleanly and save workspace state, straggler children are reaped next, and only `--force` escalates to SIGKILL.

### 5. View Instance Logs
Background launches now write stdout/stderr to `~/.antigravity-profiles/<name>/logs/`, so startup failures, sign-in and token-refresh issues are no longer invisible:
```bash
pgrav logs zwe         # tail of the latest launch log
pgrav logs zwe -f      # follow live output
pgrav logs zwe -n 200  # last 200 lines
```

### 6. Inspect Profile Details
```bash
pgrav info zwe
# scripts/CI: pgrav info zwe --json
```

### 7. Delete a Profile
```bash
pgrav delete zwe
```

### 8. Modern Web Console & Floating Widget
Manage all your instances visually with zero dependencies:
```bash
# Launch full Web Console (Matrix grid, batch controls, macOS window tiling)
pgrav web
# or simply:
pgrav ui

# Launch compact floating widget HUD
pgrav widget
# or:
pgrav ui --widget
```
*Tip: Visit `http://127.0.0.1:3888` for the full console or `http://127.0.0.1:3888/widget` for the compact HUD view.*

---

## 🗑️ Uninstall

```bash
# Remove the CLI (skip the brew line if you didn't use Homebrew)
brew uninstall paragravity   # or: rm ~/.local/bin/paragravity ~/.local/bin/pgrav

# Remove every profile sandbox (⚠️ permanently deletes all sign-in state and data)
rm -rf ~/.antigravity-profiles

# Remove the generated profile launchers
rm -rf ~/Applications/Antigravity\ \(*\).app

# Finally, remove the `export PATH="$HOME/.local/bin:$PATH"` line install.sh
# appended to your shell rc file, if present.
```

---

## 🔐 Security Notes

- Each profile stores its Google OAuth token as a **plaintext file** inside the sandbox (`~/.antigravity-profiles/<name>/home/.gemini/jetski-standalone-oauth-token`). Profile directories are created with `0700` permissions, but don't sync or back up `~/.antigravity-profiles` to cloud drives or repositories.
- For developer comfort, profile homes symlink some real locations by default (`full` policy: `~/.ssh`, `~/.config`, `~/.gitconfig`, `Desktop`, `Documents`, `Downloads`, …). That means an agent running inside a profile can read those real files. Tighten it at creation time with `--links minimal` (skips the sensitive dotdirs) or `--links none` (keychain bridge only), or override per launch with `launch --links`.

---

## 🏗️ Technical Architecture

ParaGravity achieves completely clean, isolated execution through three native mechanisms:

```text
┌──────────────────────────────────────────────────────────────┐
│                    macOS Host Environment                    │
│                                                              │
│  [Official App]          [Profile A: zwe]    [Profile B: work]
│  /Applications/          ~/.antigravity-     ~/.antigravity- 
│  Antigravity.app         profiles/zwe        profiles/work   
│  (washingshop account)   (zwe account)       (work account)  
│                                                              │
│  ├── default Library/    ├── data/           ├── data/       
│  └── default Keychain    └── home/           └── home/       
│                              ├── .gemini/        ├── .gemini/
│                              └── isolated        └── isolated
│                                  tokens              tokens  
└──────────────────────────────────────────────────────────────┘
```

1. **Storage Sandboxing (`--user-data-dir`)**: Each profile maintains its own Chromium partition, SQLite databases, IndexedDB, extensions, and workspace state.
2. **Environment & Keychain Isolation (`SSH_CONNECTION=1`)**: Electron/Language Server automatically falls back to file-based token storage within the profile's isolated directory, preventing keychain contention with the host instance.
3. **Native macOS Application Bundles**: Every profile has a dedicated `.app` bundle registered in `~/Applications`, making Antigravity multi-instance a first-class citizen in macOS.

---

## 🤝 Contributing

Contributions are warmly welcomed! Please feel free to submit an Issue or Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 👥 Contributors

Huge thanks to the contributors who helped shape ParaGravity:

- [@Kimberlying](https://github.com/Kimberlying) (Kimberly Qian) — Modern Web Console UI, dynamic multi-instance matrix layout, and batch launch dock.
- [@realdahuang](https://github.com/realdahuang) — Threat model auditing, configuration inheritance security design, and Windows cross-platform architecture.

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

---

## ⚠️ Disclaimer

ParaGravity is an open-source utility that leverages standard Chromium command-line options. It is not affiliated with, sponsored by, or endorsed by Google LLC. All trademarks belong to their respective owners.
