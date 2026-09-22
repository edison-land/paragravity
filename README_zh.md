# 🌌 ParaGravity (`pgrav`)

> **Google Antigravity 原生非侵入式多账号并行与沙盒管理器。**  
> 支持在 macOS 上同时并行开启多个独立的 Antigravity 窗口，左右分屏协同开发，彻底解决单账号配额限制。

[English](README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-yellow.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

---

## ✨ 核心优势

- 🚀 **真正的多实例并发**：支持多个 Google Gemini Pro 账号同时打开独立窗口、并排写代码，无需重启应用或频繁切换会话。
- 🛡️ **100% 零侵入安全架构**：纯粹基于 Chromium/Electron 官方标准 `--user-data-dir` 隔离。绝不给二进制打补丁、不篡改内部 SQLite 数据库，零封号与配置损坏风险。
- 🔑 **纯官方原生 OAuth**：完整保留官方 Google Cloud 登录与鉴权链路，浏览器授权跳转与 Token 自动刷新 100% 丝滑顺畅。
- 🔍 **macOS 原生系统集成**：自动在系统生成带专属图标的独立 `.app`，可直接通过 **Spotlight (`Cmd + Space`)** 键入名字秒级直达。
- ⚡ **零后台常驻与极度轻量**：没有吃内存的常驻守护进程（闲置内存占用 0 MB）。纯 Python 3 驱动，零外部 pip 或 npm 依赖。（macOS 的 `python3` 由 Xcode 命令行工具提供，缺失时执行 `xcode-select --install` 即可；`PATH` 上任意 ≥ 3.8 的 Python 也可用。）
- 🗂️ **环境物理级硬隔离**：每个分身拥有完全独立的插件扩展、本地存储、IndexedDB 与聊天记录，开发环境与主账号互不干扰。

---

## 🚀 快速安装

### 1. 一键命令行安装（推荐）

打开终端直接运行：

```bash
curl -fsSL https://raw.githubusercontent.com/edison-land/paragravity/main/install.sh | bash
```

### 2. Homebrew 安装（即将推出）

```bash
brew tap edison-land/tap
brew install paragravity
```

---

## 📖 命令行使用指南

> 💡 **小提示**：命令支持极速简写 `pgrav` 与完整名称 `paragravity`，两者完全等价！

### 1. 一键创建隔离分身
只需一条命令即可创建一个全新的独立沙盒实例：
```bash
pgrav create zwe
```
该命令会自动：
- 在 `~/.antigravity-profiles/zwe` 初始化完全独立的配置沙箱；
- 在 `~/Applications` 生成原生应用程序 `Antigravity (zwe).app`；
- 在 `~/Applications` 生成原生应用程序 `Antigravity (zwe).app`，Spotlight 会自动索引该目录，用 **Spotlight (`Cmd + Space`)** 搜索即可直达；

若想在创建后立刻启动窗口，加上 `--launch` 即可：
```bash
pgrav create work --launch
```

如果不想把真实的 `~/.ssh`、`~/.config` 暴露给分身内运行的 Agent，可以用 `--links` 收紧软链策略（默认 `full` 保持原行为）：
```bash
pgrav create work --links minimal   # 链接 git/shell 配置和常用项目目录，跳过 .ssh/.config
pgrav create work --links none      # 几乎不链接任何真实目录（仅保留钥匙串桥接）
```

### 2. 查看所有分身状态
查看所有分身、当前进程运行状态、以及绑定的 Google 账号：
```bash
pgrav list
# 或者简写：
pgrav ls
```

> 💡 目录大小会全量遍历分身文件，分身很大时比较慢，因此默认不显示。需要时用 `pgrav list --size`；脚本/CI 里可用 `pgrav list --json` 拿到机器可读输出。

**终端输出示例：**
```text
PROFILE            STATUS         PID      ACCOUNT (GOOGLE)               SIZE       DESCRIPTION
───────────────────────────────────────────────────────────────────────────────────────────────
zwe                ● Running      49377    zwe.dev@gmail.com              —          开发主账号
work               ○ Stopped      -        work@company.com               —          公司业务账号
```

### 3. 启动分身
```bash
pgrav launch zwe
```
*或者直接在 Mac 任意位置按 `Cmd + Space` 键入 `Antigravity (zwe)` 回车启动！*

启动时可以直接带上要打开的项目目录：
```bash
pgrav launch zwe ~/Projects/demo
```

### 4. 停止运行中的分身
```bash
pgrav stop zwe
```
停止是分阶段进行的：先让主进程优雅退出并保存工作区状态，再清理残留子进程；卡住时才用 `--force` 强杀。

### 5. 查看分身日志
后台启动的窗口日志落在 `~/.antigravity-profiles/<名字>/logs/`，方便排查启动失败、登录与 token 刷新问题：
```bash
pgrav logs zwe         # 查看最近一次启动日志的末尾
pgrav logs zwe -f      # 实时跟踪输出
pgrav logs zwe -n 200  # 显示最后 200 行
```

### 6. 查看分身详细诊断信息
```bash
pgrav info zwe
# 脚本里可用：pgrav info zwe --json
```

### 7. 一键删除分身
清理分身沙盒数据及其 macOS 快捷图标：
```bash
pgrav delete zwe
```

---

## 🗑️ 卸载

```bash
# 移除 CLI（没用 Homebrew 装的话跳过 brew 那行）
brew uninstall paragravity   # 或者：rm ~/.local/bin/paragravity ~/.local/bin/pgrav

# 移除所有分身沙盒（⚠️ 永久删除全部登录状态与数据）
rm -rf ~/.antigravity-profiles

# 移除生成的分身启动图标
rm -rf ~/Applications/Antigravity\ \(*\).app

# 最后，把 install.sh 追加到 shell rc 文件里的
# `export PATH="$HOME/.local/bin:$PATH"` 一行删掉（如果存在）
```

---

## 🔐 安全须知

- 每个分身的 Google OAuth Token 以**明文文件**形式存放在沙盒内（`~/.antigravity-profiles/<name>/home/.gemini/jetski-standalone-oauth-token`）。分身目录以 `0700` 权限创建，但请不要把 `~/.antigravity-profiles` 同步到网盘或提交进仓库。
- 出于开发便利考虑，分身的假 HOME 默认（`full` 策略）会软链部分真实目录（`~/.ssh`、`~/.config`、`~/.gitconfig`、`Desktop`、`Documents`、`Downloads` 等），这意味着分身内运行的 Agent 可以读到这些真实文件。创建分身时用 `--links minimal`（跳过 `.ssh`/`.config` 等敏感点目录）或 `--links none`（几乎不链接）即可收紧，无需改代码。`launch --links` 也可以临时覆盖。

---

## 🏗️ 底层架构原理

ParaGravity 通过三层原生机制实现安全隔离：

```text
┌──────────────────────────────────────────────────────────────┐
│                    macOS 宿主系统环境                         │
│                                                              │
│  [官方默认主应用]          [分身 A: zwe]       [分身 B: work] 
│  /Applications/          ~/.antigravity-     ~/.antigravity- 
│  Antigravity.app         profiles/zwe        profiles/work   
│  (主账号 washingshop)     (账号 zwe)          (账号 work)     
│                                                              │
│  ├── 默认系统 Library     ├── 独立 data/      ├── 独立 data/  
│  └── 默认 Keychain 钥匙串 └── 独立 home/      └── 独立 home/  
│                              ├── .gemini/        ├── .gemini/
│                              └── 隔离 Token      └── 隔离 Token
└──────────────────────────────────────────────────────────────┘
```

1. **存储数据硬隔离 (`--user-data-dir`)**：为每个实例指定独立的用户数据目录，Chromium 的进程树、存储区、数据库、扩展与工作区配置天然物理隔离。
2. **钥匙串争抢避让 (`SSH_CONNECTION=1`)**：引导底层语言服务降级使用沙箱内部文件存储 Token，避免多个实例同时向 macOS 共享系统钥匙串读写而发生冲突。
3. **macOS 独立应用包**：为每个分身独立编译 macOS Bundle，让多实例成为 macOS 的一等公民。

---

## 🤝 参与贡献

非常欢迎提交 Issue 或 Pull Request！

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的修改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 新建 Pull Request

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 协议开源。

---

## ⚠️ 免责声明

ParaGravity 是一个利用 Chromium 官方命令行特性的开源管理工具，与 Google LLC 官方无隶属或直接关联关系。所有品牌及商标均归其各自所有者所有。
