#!/usr/bin/env python3
"""Life2English · 本地 Web 界面服务（零第三方依赖）。

仅使用 Python 标准库 http.server：
- 静态文件：web/ 目录下的 index.html / app.js / style.css
- API 路由：POST /api/<action>，请求体为 JSON，直接转发给 skill_api.handle()
  （界面与命令行共用同一套业务逻辑，不存在第二份实现）

启动：
    python scripts/web_server.py            # 默认 http://127.0.0.1:8770（仅本机）
    python scripts/web_server.py --port 9000 --no-browser

部署环境：
    未显式指定 --host/--port 时，自动读取环境变量 PORT；
    一旦检测到 PORT（说明运行在托管环境），默认绑定 0.0.0.0，否则保持 127.0.0.1。
    这样本地运行仍是「仅本机可访问」，部署时无需改代码即可被反向代理访问。

安全说明：本地默认仅绑定 127.0.0.1，不对外网开放。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import skill_api  # noqa: E402

WEB_DIR = _HERE.parent / "web"

# 托管环境（如发布平台）会注入 PORT；本地运行时通常没有该变量。
_ENV_PORT = os.environ.get("PORT")
_DEFAULT_PORT = int(_ENV_PORT) if _ENV_PORT and _ENV_PORT.isdigit() else 8770
_DEFAULT_HOST = "0.0.0.0" if _ENV_PORT else "127.0.0.1"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Life2English/1.3"

    # -- 工具方法 -----------------------------------------------------------
    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"ok": False, "error": f"未找到：{path.name}"}, status=404)
            return
        data = path.read_bytes()
        ctype = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # -- 路由 ---------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html")
        elif route == "/api/version":
            self._send_json(skill_api.handle({"action": "version"}))
        elif route == "/api/scenes":
            self._send_json(skill_api.handle({"action": "list_scenes"}))
        elif route.startswith("/api/"):
            self._send_json(
                {"ok": False, "error": "该接口仅支持 POST，请携带 JSON 请求体"},
                status=405,
            )
        else:
            # 静态资源：只允许 web/ 目录内的文件，禁止路径穿越
            rel = route.lstrip("/")
            candidate = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() in candidate.parents and candidate.is_file():
                self._send_file(candidate)
            else:
                self._send_file(WEB_DIR / "index.html")

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if not route.startswith("/api/"):
            self._send_json({"ok": False, "error": "未知接口"}, status=404)
            return

        action = route[len("/api/"):]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": f"JSON 解析失败：{exc}"}, status=400)
            return

        if "action" not in payload:
            payload["action"] = action
        self._send_json(skill_api.handle(payload))

    def log_message(self, fmt: str, *args) -> None:  # 降低日志噪音
        sys.stderr.write("[web] %s\n" % (fmt % args))


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Life2English 本地 Web 界面")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT,
                        help=f"监听端口（默认 {_DEFAULT_PORT}；环境变量 PORT 优先）")
    parser.add_argument("--host", default=_DEFAULT_HOST,
                        help=f"监听地址（默认 {_DEFAULT_HOST}）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    if not (WEB_DIR / "index.html").exists():
        print(f"[错误] 未找到界面文件：{WEB_DIR / 'index.html'}")
        sys.exit(1)

    url = f"http://{args.host}:{args.port}/"
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 60)
    print("Life2English · 生活场景驱动的英语学习")
    print("=" * 60)
    print(f"界面地址：{url}")
    if args.host == "127.0.0.1":
        print("（仅本机可访问；按 Ctrl+C 停止服务）")
    else:
        print(f"（监听 {args.host}，可供外部访问；按 Ctrl+C 停止服务）")
    print("=" * 60)

    # 仅在本地回环地址上自动打开浏览器；托管环境下不弹窗
    if not args.no_browser and args.host in ("127.0.0.1", "localhost"):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
