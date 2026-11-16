#!/usr/bin/env python3
"""
Lightweight Web Console & Widget Server for ParaGravity.
Serves the React dashboard and provides a REST API using only the Python standard library.
"""

from __future__ import annotations

import os
import sys
import json
import time
import mimetypes
import webbrowser
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

try:
    from http.server import ThreadingHTTPServer
except ImportError:
    import socketserver
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True

REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_CLI = Path(__file__).resolve().parent / "paragravity"
CLI_PATH = _LOCAL_CLI if _LOCAL_CLI.is_file() else (REPO_ROOT / "bin" / "paragravity")
DASHBOARD_DIST = REPO_ROOT / "dashboard" / "dist"

# mimetypes reads the Windows registry and may report .js as text/plain, which
# makes browsers refuse to execute module scripts — pin the web essentials.
MIME_OVERRIDES = {
    ".js": "text/javascript", ".mjs": "text/javascript",
    ".css": "text/css", ".json": "application/json",
    ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml",
    ".woff": "font/woff", ".woff2": "font/woff2",
    ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon",
}

# Tiny TTL cache so a polling dashboard doesn't spawn a CLI subprocess on
# every request when several widgets/tabs are open at once.
_profiles_cache = {"t": 0.0, "body": b"[]"}
PROFILES_CACHE_TTL = 1.0

WIDGET_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ParaGravity 悬浮挂件 HUD</title>
    <style>
        :root {
            --bg: #0F172A;
            --card-bg: rgba(30, 41, 59, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --accent: #6366F1;
            --cyan: #22D3EE;
            --green: #10B981;
            --red: #EF4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 16px;
            font-size: 13px;
            user-select: none;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        .title {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            font-weight: 600;
        }
        .badge {
            font-size: 10px;
            background: rgba(99, 102, 241, 0.2);
            color: #A5B4FC;
            padding: 2px 6px;
            border-radius: 999px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .cli-bar {
            background: rgba(34, 211, 238, 0.08);
            border: 1px solid rgba(34, 211, 238, 0.2);
            border-radius: 8px;
            padding: 7px 10px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
        }
        .profile-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 400px;
            overflow-y: auto;
        }
        .profile-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            transition: all 0.2s ease;
        }
        .profile-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-1px);
        }
        .profile-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .profile-name {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-dot.running { background: var(--green); box-shadow: 0 0 6px var(--green); }
        .status-dot.stopped { background: #64748B; }
        .profile-account {
            font-size: 11px;
            color: var(--text-muted);
        }
        .cli-pill {
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 999px;
            background: rgba(34, 211, 238, 0.15);
            color: var(--cyan);
            border: 1px solid rgba(34, 211, 238, 0.35);
        }
        .btn-group {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }
        .btn {
            border: none;
            padding: 5px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.85; }
        .btn-launch { background: var(--accent); color: white; }
        .btn-cli { background: rgba(34, 211, 238, 0.14); color: #67E8F9; border: 1px solid rgba(34, 211, 238, 0.3); }
        .btn-stop { background: rgba(239, 68, 68, 0.2); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.3); }
        .footer {
            margin-top: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text-muted);
        }
        .link {
            color: var(--accent);
            text-decoration: none;
            cursor: pointer;
        }
        .link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">
            <span>🐾 ParaGravity</span>
            <span class="badge" id="running-count">0 活跃</span>
        </div>
        <a class="link" href="/" target="_blank">🖥️ 打开矩阵控制台</a>
    </div>

    <div class="cli-bar">
        <span id="cli-status">agy CLI: 加载中...</span>
        <div class="btn-group">
            <button class="btn btn-cli" onclick="switchCLI('host')">Host CLI</button>
            <button class="btn btn-cli" onclick="triggerSync()">同步</button>
        </div>
    </div>

    <div class="profile-list" id="profiles-container">
        <div style="text-align:center;padding:20px;color:var(--text-muted);">正在加载分身...</div>
    </div>

    <div class="footer">
        <span id="refresh-indicator">● 实时同步</span>
        <span class="link" onclick="fetchAll()">刷新</span>
    </div>

    <script>
        const esc = s => String(s ?? '').replace(/[&<>"']/g,
            c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

        async function fetchAll() {
            try {
                const [profRes, cliRes] = await Promise.all([
                    fetch('/api/profiles'),
                    fetch('/api/cli')
                ]);
                const data = await profRes.json();
                const cliData = await cliRes.json();
                renderCLI(cliData);
                renderProfiles(data);
            } catch (err) {
                console.error(err);
            }
        }

        function renderCLI(cliData) {
            const cur = cliData.current || {};
            const sync = cliData.sync || {};
            const el = document.getElementById('cli-status');
            el.innerHTML = `agy CLI: <b style="color:#67E8F9;">${esc(cur.active_profile || 'host')}</b> (${esc(cur.account || '未登录')})`;
            const ind = document.getElementById('refresh-indicator');
            const counts = sync.shared_counts || {};
            ind.textContent = `${sync.daemon_running ? '●' : '○'} 实时同步 (${counts.projects || 0}P/${counts.skills || 0}S)`;
        }

        function renderProfiles(profiles) {
            const container = document.getElementById('profiles-container');
            const runningCount = profiles.filter(p => p.running).length;
            document.getElementById('running-count').textContent = `${runningCount} 活跃`;

            if (profiles.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">暂无分身，请在终端执行 pgrav create 创建</div>';
                return;
            }

            container.innerHTML = profiles.map(p => `
                <div class="profile-card">
                    <div class="profile-info">
                        <div class="profile-name">
                            <span class="status-dot ${p.running ? 'running' : 'stopped'}"></span>
                            <span>${esc(p.name)}</span>
                            ${p.running ? `<span style="font-size:10px;color:#94A3B8;">(PID: ${esc(p.pid)})</span>` : ''}
                            ${p.active_cli ? `<span class="cli-pill">★ agy CLI</span>` : ''}
                        </div>
                        <div class="profile-account">${esc(p.account || '(未绑定 Google 账号)')}</div>
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-cli" onclick="switchCLI('${esc(p.name)}')">切换CLI</button>
                        ${p.running
                            ? `<button class="btn btn-stop" onclick="stopProfile('${esc(p.name)}')">停止</button>`
                            : `<button class="btn btn-launch" onclick="launchProfile('${esc(p.name)}')">启动</button>`
                        }
                    </div>
                </div>
            `).join('');
        }

        async function launchProfile(name) {
            await fetch(`/api/profiles/${encodeURIComponent(name)}/launch`, { method: 'POST' });
            setTimeout(fetchAll, 500);
        }

        async function stopProfile(name) {
            await fetch(`/api/profiles/${encodeURIComponent(name)}/stop`, { method: 'POST' });
            setTimeout(fetchAll, 500);
        }

        async function switchCLI(name) {
            await fetch('/api/cli/use', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            setTimeout(fetchAll, 250);
        }

        async function triggerSync() {
            await fetch('/api/sync', { method: 'POST' });
            setTimeout(fetchAll, 250);
        }

        fetchAll();
        setInterval(fetchAll, 2500);
    </script>
</body>
</html>
"""

STANDALONE_CONSOLE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ParaGravity 控制台</title>
    <style>
        :root {
            --bg: #F8F9FD;
            --card-bg: #FFFFFF;
            --text-main: #1E1B4B;
            --text-muted: #64748B;
            --accent: #4F46E5;
            --border: #E2E8F0;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #0F172A;
                --card-bg: #1E293B;
                --text-main: #F8FAFC;
                --text-muted: #94A3B8;
                --accent: #6366F1;
                --border: rgba(255, 255, 255, 0.1);
            }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 32px 24px;
            max-width: 1100px;
            margin: 0 auto;
        }
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        h1 { font-size: 24px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .status-strip {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }
        .status-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 13px;
        }
        .banner {
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 20px;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .actions-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        .btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.9; }
        .btn-outline {
            background: transparent;
            color: var(--text-main);
            border: 1px solid var(--border);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .card-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .status-badge {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 999px;
            font-weight: 600;
        }
        .status-running { background: rgba(16, 185, 129, 0.15); color: #10B981; }
        .status-stopped { background: rgba(100, 116, 139, 0.15); color: #64748B; }
        .cli-badge {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(6, 182, 212, 0.15);
            color: #06B6D4;
            border: 1px solid rgba(6, 182, 212, 0.3);
        }
        .card-account { font-size: 12px; color: var(--text-muted); }
        .card-actions { display: flex; gap: 8px; flex-wrap: wrap; }
    </style>
</head>
<body>
    <header>
        <h1>🌌 ParaGravity Web Console</h1>
        <div>
            <a class="btn btn-outline" href="/widget" target="_blank" style="text-decoration:none;">🐾 悬浮挂件 (Widget)</a>
        </div>
    </header>

    <div class="status-strip">
        <div class="status-group">
            <div id="cli-binding">终端 <code>agy</code> CLI 绑定: 加载中...</div>
            <div id="sync-engine" class="card-account">实时同步引擎: 检测中...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn btn-outline" onclick="switchCLI('host')">切回本机 Host CLI</button>
            <button class="btn btn-outline" onclick="triggerSync()">🔄 立即同步</button>
        </div>
    </div>

    <div class="banner">
        <div>💡 <b>提示</b>：Projects / Skills / Plugins / Hooks 与 <code>agy</code> CLI 均已支持跨分身与宿主机同步。</div>
        <a class="btn btn-outline" style="font-size:11px;padding:4px 8px;text-decoration:none;" href="https://github.com/edison-land/paragravity" target="_blank">GitHub</a>
    </div>

    <div class="actions-bar">
        <button class="btn" onclick="batchLaunch()">🚀 一键启动全部</button>
        <button class="btn btn-outline" onclick="batchStop()">⏹ 一键停止全部</button>
        <button class="btn btn-outline" onclick="tileWindows()">🪟 智能平铺窗口 (macOS)</button>
        <button class="btn btn-outline" onclick="fetchAll()">🔄 刷新列表</button>
    </div>

    <div class="grid" id="profile-grid">
        <div style="color:var(--text-muted);grid-column:1/-1;">正在加载分身...</div>
    </div>

    <script>
        const esc = s => String(s ?? '').replace(/[&<>"']/g,
            c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

        async function fetchAll() {
            try {
                const [profRes, cliRes] = await Promise.all([
                    fetch('/api/profiles'),
                    fetch('/api/cli')
                ]);
                const data = await profRes.json();
                const cliData = await cliRes.json();
                renderStatusStrip(cliData);
                renderGrid(data);
            } catch (err) {
                console.error(err);
            }
        }

        function renderStatusStrip(cliData) {
            const cur = cliData.current || {};
            const sync = cliData.sync || {};
            const counts = sync.shared_counts || {};
            document.getElementById('cli-binding').innerHTML =
                `当前终端 <code>agy</code> CLI 绑定: <b>${esc(cur.active_profile || 'host')}</b> (${esc(cur.account || '未登录')})`;
            document.getElementById('sync-engine').innerHTML =
                `实时同步引擎: <b style="color:${sync.daemon_running ? '#10B981' : '#94A3B8'};">${sync.daemon_running ? '● 已连通' : '○ 未启动'}</b> (${counts.projects || 0} Projects / ${counts.skills || 0} Skills / ${counts.plugins || 0} Plugins)`;
        }

        function renderGrid(profiles) {
            const grid = document.getElementById('profile-grid');
            if (profiles.length === 0) {
                grid.innerHTML = '<div style="color:var(--text-muted);grid-column:1/-1;">暂无分身，请在终端执行 pgrav create &lt;name&gt; 创建</div>';
                return;
            }
            grid.innerHTML = profiles.map(p => `
                <div class="card">
                    <div>
                        <div class="card-header">
                            <span class="card-title">
                                ${esc(p.name)}
                                ${p.active_cli ? `<span class="cli-badge">★ agy CLI</span>` : ''}
                            </span>
                            <span class="status-badge ${p.running ? 'status-running' : 'status-stopped'}">
                                ${p.running ? `● 运行中 (${esc(p.pid)})` : '○ 已停止'}
                            </span>
                        </div>
                        <div class="card-account" style="margin-top:8px;">${esc(p.account || '(未绑定 Google 账号)')}</div>
                        <div class="card-account" style="margin-top:4px;font-size:11px;">目录: ${esc(p.directory || '-')}</div>
                    </div>
                    <div class="card-actions">
                        ${p.running
                            ? `<button class="btn btn-outline" style="color:#EF4444;border-color:rgba(239,68,68,0.3);" onclick="stopProfile('${esc(p.name)}')">停止</button>`
                            : `<button class="btn" onclick="launchProfile('${esc(p.name)}')">启动窗口</button>`
                        }
                        <button class="btn btn-outline" onclick="switchCLI('${esc(p.name)}')">切换 agy CLI</button>
                        <button class="btn btn-outline" onclick="deleteProfile('${esc(p.name)}')">删除</button>
                    </div>
                </div>
            `).join('');
        }

        async function launchProfile(name) {
            await fetch(`/api/profiles/${encodeURIComponent(name)}/launch`, { method: 'POST' });
            setTimeout(fetchAll, 600);
        }

        async function stopProfile(name) {
            await fetch(`/api/profiles/${encodeURIComponent(name)}/stop`, { method: 'POST' });
            setTimeout(fetchAll, 600);
        }

        async function deleteProfile(name) {
            if (!confirm(`确定要删除分身 '${name}' 吗？`)) return;
            await fetch(`/api/profiles/${encodeURIComponent(name)}`, { method: 'DELETE' });
            setTimeout(fetchAll, 600);
        }

        async function switchCLI(name) {
            await fetch('/api/cli/use', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            setTimeout(fetchAll, 300);
        }

        async function triggerSync() {
            await fetch('/api/sync', { method: 'POST' });
            setTimeout(fetchAll, 300);
        }

        async function batchLaunch() {
            await fetch('/api/batch/launch', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({names: []}) });
            setTimeout(fetchAll, 800);
        }

        async function batchStop() {
            await fetch('/api/batch/stop', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({names: []}) });
            setTimeout(fetchAll, 800);
        }

        async function tileWindows() {
            const res = await fetch('/api/tile', { method: 'POST' });
            const data = await res.json();
            if (!data.success && data.error) alert(data.error);
        }

        fetchAll();
        setInterval(fetchAll, 3000);
    </script>
</body>
</html>
"""

class ParaGravityHandler(BaseHTTPRequestHandler):
    def check_origin(self) -> bool:
        origin = self.headers.get("Origin") or self.headers.get("Referer")
        if not origin:
            return True
        parsed = urlparse(origin)
        return parsed.hostname in ("127.0.0.1", "localhost", None)

    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname in ("127.0.0.1", "localhost"):
                self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path.startswith("/api/") and not self.check_origin():
            self.send_error(403, "Forbidden: Cross-origin request rejected")
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/profiles":
            self.handle_get_profiles()
            return
        elif path == "/api/cli":
            self.handle_get_cli()
            return
        elif path == "/api/system":
            self.send_json({
                "version": "1.3.0",
                "theme": "dawn-iris",
                "themeName": "晨曦紫霞白 (Dawn Iris & Violet)",
                "platform": sys.platform,
            })
            return
        elif path in ("/widget", "/widget/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WIDGET_HTML.encode("utf-8"))
            return

        self.serve_static(path)

    def do_POST(self):
        if not self.check_origin():
            self.send_error(403, "Forbidden: Cross-origin request rejected")
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/profiles":
            self.handle_create_profile()
            return

        if path == "/api/cli/use":
            self.handle_use_cli()
            return

        if path == "/api/sync":
            self.handle_sync_now()
            return

        # POST /api/batch/launch
        if path == "/api/batch/launch":
            self.handle_batch_launch()
            return

        # POST /api/batch/stop
        if path == "/api/batch/stop":
            self.handle_batch_stop()
            return

        # POST /api/tile
        if path == "/api/tile":
            self.handle_tile_windows()
            return

        # POST /api/profiles/<name>/launch
        parts = [p for p in path.split("/") if p]
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "profiles" and parts[3] == "launch":
            name = unquote(parts[2])
            self.handle_launch_profile(name)
            return

        # POST /api/profiles/<name>/stop
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "profiles" and parts[3] == "stop":
            name = unquote(parts[2])
            self.handle_stop_profile(name)
            return

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        if not self.check_origin():
            self.send_error(403, "Forbidden: Cross-origin request rejected")
            return

        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "profiles":
            name = unquote(parts[2])
            self.handle_delete_profile(name)
            return

        self.send_error(404, "Endpoint not found")

    def _profiles_json_bytes(self) -> bytes:
        """Run `list --json` and return a guaranteed-JSON payload.

        Served from a short TTL cache; a non-JSON CLI output can never leak
        into an application/json response body.
        """
        now = time.time()
        if now - _profiles_cache["t"] < PROFILES_CACHE_TTL:
            return _profiles_cache["body"]
        try:
            out = subprocess.check_output([sys.executable, str(CLI_PATH), "list", "--json"], text=True)
            payload = out.strip() or "[]"
            json.loads(payload)  # validate before caching/serving
        except Exception:
            payload = "[]"
        _profiles_cache["t"] = now
        _profiles_cache["body"] = payload.encode("utf-8")
        return _profiles_cache["body"]

    def handle_get_profiles(self):
        try:
            body = self._profiles_json_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_get_cli(self):
        try:
            cur_res = subprocess.run([sys.executable, str(CLI_PATH), "current", "--json"], capture_output=True, text=True)
            sync_res = subprocess.run([sys.executable, str(CLI_PATH), "sync", "status", "--json"], capture_output=True, text=True)
            cur_data = json.loads(cur_res.stdout) if cur_res.returncode == 0 and cur_res.stdout.strip() else {}
            sync_data = json.loads(sync_res.stdout) if sync_res.returncode == 0 and sync_res.stdout.strip() else {}
            self.send_json({"current": cur_data, "sync": sync_data})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_use_cli(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body or "{}")
            name = str(data.get("name", "")).strip()
            if not name:
                self.send_json({"error": "Profile name or 'host' is required"}, status=400)
                return
            res = subprocess.run([sys.executable, str(CLI_PATH), "use", name], capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "active": name, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to switch CLI profile"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_sync_now(self):
        try:
            res = subprocess.run([sys.executable, str(CLI_PATH), "sync", "now"], capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to sync"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_create_profile(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body or "{}")
            name = data.get("name", "").strip()
            desc = data.get("description", "")
            launch = data.get("launch", False)

            if not name:
                self.send_json({"error": "Profile name is required"}, status=400)
                return

            cmd = [sys.executable, str(CLI_PATH), "create", name]
            if desc:
                cmd.extend(["-d", desc])
            if launch:
                cmd.append("-l")

            res = subprocess.run(cmd, capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to create profile"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_launch_profile(self, name: str):
        try:
            res = subprocess.run([sys.executable, str(CLI_PATH), "launch", name], capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to launch"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_stop_profile(self, name: str):
        try:
            res = subprocess.run([sys.executable, str(CLI_PATH), "stop", name, "--force"], capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to stop"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_delete_profile(self, name: str):
        try:
            res = subprocess.run([sys.executable, str(CLI_PATH), "delete", name, "-f"], capture_output=True, text=True)
            _profiles_cache["t"] = 0.0
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout})
            else:
                self.send_json({"error": res.stderr or res.stdout or "Failed to delete"}, status=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_batch_launch(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body or "{}")
            names = data.get("names", [])
            if not names:
                profiles = json.loads(self._profiles_json_bytes())
                names = [p["name"] for p in profiles if not p.get("running")]

            results = []
            for name in names:
                res = subprocess.run([sys.executable, str(CLI_PATH), "launch", name], capture_output=True, text=True)
                results.append({
                    "name": name,
                    "success": res.returncode == 0,
                    "output": (res.stdout or res.stderr or "").strip()
                })
            self.send_json({"success": True, "results": results})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_batch_stop(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body or "{}")
            names = data.get("names", [])
            if not names:
                profiles = json.loads(self._profiles_json_bytes())
                names = [p["name"] for p in profiles if p.get("running")]

            results = []
            for name in names:
                res = subprocess.run([sys.executable, str(CLI_PATH), "stop", name, "--force"], capture_output=True, text=True)
                results.append({
                    "name": name,
                    "success": res.returncode == 0,
                    "output": (res.stdout or res.stderr or "").strip()
                })
            self.send_json({"success": True, "results": results})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_tile_windows(self):
        if sys.platform != "darwin":
            self.send_json({"success": False, "error": "Window tiling is supported on macOS only."}, status=400)
            return

        script = """
        tell application "Finder"
            set b to bounds of window of desktop
            set screenW to item 3 of b
            set screenH to item 4 of b
        end tell

        tell application "System Events"
            set appProcs to (every application process whose name contains "Antigravity")
            set allWins to {}
            repeat with p in appProcs
                try
                    set winList to every window of p
                    repeat with w in winList
                        set end of allWins to {proc:p, win:w}
                    end repeat
                end try
            end repeat
            
            set winCount to count of allWins
            if winCount is 0 then return "no_windows"
            
            if winCount is 1 then
                set wObj to item 1 of allWins
                set position of (win of wObj) to {60, 60}
                set size of (win of wObj) to {screenW - 120, screenH - 120}
            else if winCount is 2 then
                set halfW to (screenW / 2) as integer
                set w1 to item 1 of allWins
                set w2 to item 2 of allWins
                set position of (win of w1) to {0, 30}
                set size of (win of w1) to {halfW, screenH - 30}
                set position of (win of w2) to {halfW, 30}
                set size of (win of w2) to {halfW, screenH - 30}
            else if winCount is 3 then
                set thirdW to (screenW / 3) as integer
                repeat with i from 1 to 3
                    set wObj to item i of allWins
                    set position of (win of wObj) to {(i - 1) * thirdW, 30}
                    set size of (win of wObj) to {thirdW, screenH - 30}
                end repeat
            else
                set halfW to (screenW / 2) as integer
                set halfH to ((screenH - 30) / 2) as integer
                set coords to {{0, 30}, {halfW, 30}, {0, 30 + halfH}, {halfW, 30 + halfH}}
                repeat with i from 1 to 4
                    if i <= winCount then
                        set wObj to item i of allWins
                        set c to item i of coords
                        set position of (win of wObj) to c
                        set size of (win of wObj) to {halfW, halfH}
                    end if
                end repeat
            end if
            return "ok"
        end tell
        """
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                self.send_json({"success": True, "output": res.stdout.strip()})
            else:
                self.send_json({"success": False, "error": res.stderr.strip() or "Window tiling requires Accessibility permission."})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def serve_static(self, path: str):
        index_file = DASHBOARD_DIST / "index.html"
        if not index_file.is_file():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(STANDALONE_CONSOLE_HTML.encode("utf-8"))
            return

        rel_path = unquote(path).lstrip("/")
        dist_root = DASHBOARD_DIST.resolve()
        target = (dist_root / rel_path).resolve()

        # Path traversal guard: the resolved target must stay inside dist/.
        # `/../../secret` or %2e%2e sequences must never escape the docroot.
        try:
            target.relative_to(dist_root)
        except ValueError:
            self.send_error(403, "Forbidden")
            return

        # SPA fallback to index.html if file doesn't exist
        if not target.is_file():
            target = index_file

        content_type = MIME_OVERRIDES.get(target.suffix.lower())
        if not content_type:
            guessed, _ = mimetypes.guess_type(str(target))
            content_type = guessed or "application/octet-stream"

        try:
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Clean terminal logging
        pass

def start_server(port: int = 3888, open_browser: bool = True, widget_mode: bool = False):
    server_address = ("127.0.0.1", port)
    try:
        httpd = ThreadingHTTPServer(server_address, ParaGravityHandler)
    except OSError:
        print(f"\033[31mError: port {port} is already in use. Pick another with: pgrav web --port <port>\033[0m", file=sys.stderr)
        sys.exit(1)
    base_url = f"http://127.0.0.1:{port}"
    target_url = f"{base_url}/widget" if widget_mode else base_url

    print(f"\033[36m🌌 ParaGravity Web Console & Widget 已启动：\033[0m \033[1m{target_url}\033[0m")
    print(f"  • 矩阵控制台: \033[1m{base_url}\033[0m")
    print(f"  • 悬浮小挂件: \033[1m{base_url}/widget\033[0m")
    print("  • 退出服务:   按 \033[1mCtrl + C\033[0m\n")

    if open_browser:
        webbrowser.open(target_url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[33mWeb Console 已停止。\033[0m")
        httpd.server_close()

if __name__ == "__main__":
    port = 3888
    widget = False
    args = sys.argv[1:]
    if "--widget" in args:
        widget = True
        args.remove("--widget")
    if args and args[0].isdigit():
        port = int(args[0])
    start_server(port, open_browser=True, widget_mode=widget)
