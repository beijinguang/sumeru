#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""须弥写作 webui 服务入口。

用法：
    cd <小说项目目录>
    python3 <仓库>/webui/server.py            # 默认端口 8765
    python3 server.py --port 9000

只绑定 127.0.0.1。工作目录 = 启动时 cwd，所有章节/中间数据以它为根。
"""

import argparse
import importlib.util
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def _load_api():
    """以文件路径加载 api 模块（webui 不是包，避免依赖 cwd）"""
    spec = importlib.util.spec_from_file_location(
        "webui_api", Path(__file__).resolve().parent / "api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


api = _load_api()
STATIC_DIR = Path(__file__).resolve().parent / "static"
ROOT = Path.cwd()


class Handler(BaseHTTPRequestHandler):
    server_version = "sumeru-webui/0.1"

    # ------------------------------------------------------------- helpers
    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _static(self, filename):
        path = STATIC_DIR / filename
        if not path.is_file():
            self._send(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._send(200, path.read_bytes(), f"{ctype}; charset=utf-8"
                   if ctype.startswith("text/") else ctype)

    # ------------------------------------------------------------- GET
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path == "/app.js":
            return self._static("app.js")
        if path == "/style.css":
            return self._static("style.css")

        try:
            if path == "/api/status":
                return self._send(*api.handle_status(ROOT))
            if path == "/api/chapters":
                return self._send(*api.list_chapters(ROOT))
            if path == "/api/outline":
                num = (qs.get("chapter") or [None])[0]
                if num is None or not num.isdigit():
                    return self._send(400, {"error": "缺少 chapter 参数"})
                return self._send(*api.get_outline_chapter(ROOT, num))
            if path == "/api/next-step":
                return self._send(*api.next_step(ROOT))
            if path.startswith("/api/chapters/"):
                num = path.rsplit("/", 1)[-1]
                if not num.isdigit():
                    return self._send(400, {"error": "章节号必须是数字"})
                outline_flag = (qs.get("outline") or ["0"])[0] == "1"
                return self._send(*api.get_chapter(ROOT, num, outline_number=outline_flag))
            if path.startswith("/api/reports/"):
                name = path[len("/api/reports/"):]
                return self._send(*api.get_report(ROOT, name))
            if path.startswith("/api/export/"):
                parts = path[len("/api/export/"):].split("/", 1)
                if len(parts) != 2:
                    return self._send(400, {"error": "格式：/api/export/{platform}/{file}"})
                code, payload = api.get_export(ROOT, parts[0], parts[1])
                if isinstance(payload, bytes):
                    self.send_response(code)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Content-Disposition",
                                     f"attachment; filename=\"{parts[1]}\"")
                    self.end_headers()
                    return self.wfile.write(payload)
                return self._send(code, payload)
            if path.startswith("/api/tools/"):
                tool = path.rsplit("/", 1)[-1]
                return self._send(*api.last_tool(tool))
            return self._send(404, {"error": f"未知路径 {path}"})
        except Exception as exc:  # 防御性兜底，保持服务可用
            return self._send(500, {"error": f"internal: {exc}"})

    # ------------------------------------------------------------- POST/PUT
    def do_POST(self):
        self._dispatch_write("POST")

    def do_PUT(self):
        self._dispatch_write("PUT")

    def do_HEAD(self):
        """导出文件存在性探测（前端下载列表用）"""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/export/"):
            parts = path[len("/api/export/"):].split("/", 1)
            code, _ = api.get_export(ROOT, parts[0], unquote(parts[1])) if len(parts) == 2 \
                else (400, None)
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _dispatch_write(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        body = self._json_body()
        if body is None:
            return self._send(400, {"error": "请求体必须是合法 JSON"})
        try:
            if method == "POST" and path.startswith("/api/tools/"):
                tool = path.rsplit("/", 1)[-1]
                args = body.get("args") if isinstance(body, dict) else None
                return self._send(*api.run_tool(ROOT, tool, args or []))
            if method == "PUT" and path.startswith("/api/chapters/"):
                num = path.rsplit("/", 1)[-1]
                if not num.isdigit():
                    return self._send(400, {"error": "章节号必须是数字"})
                content = body.get("content") if isinstance(body, dict) else None
                return self._send(*api.save_chapter(ROOT, num, content))
            return self._send(404, {"error": f"未知路径 {path}"})
        except Exception as exc:
            return self._send(500, {"error": f"internal: {exc}"})

    def log_message(self, fmt, *args):  # 安静模式：出错才打印
        pass


def main():
    parser = argparse.ArgumentParser(description="须弥写作 Web 驾驶舱")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"📖 须弥写作驾驶舱：http://127.0.0.1:{args.port}")
    print(f"   工作目录：{ROOT}")
    print("   Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
