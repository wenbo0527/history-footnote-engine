#!/usr/bin/env python3
"""🆕 v2.10.10 SPA 静态服务器

🆕 v2.10.10 从 /tmp/spa_server.py 移入 scripts/（之前是临时文件，丢失了导致
`bash scripts/dev-server.sh start spa` 直接报 file not found）。

用途：
- 用 src/frontend/build/ SvelteKit adapter-static 产物，启一个 Python http server
- 当 dev-server.sh 的 spa 模式（或纯生产 demo，不配 nginx 时）使用
- 与 nginx 服 SvelteKit 的能力等价，但单文件，零依赖

用法：
    python scripts/spa_server.py <port> <static_dir>
    python scripts/spa_server.py 5173 src/frontend/build
"""
from __future__ import annotations

import http.server
import mimetypes
import sys
from functools import partial
from pathlib import Path


# SvelteKit asset extensions
MIME_OVERRIDES = {
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".png": "image/png",
    ".webp": "image/webp",
}


class SpaHandler(http.server.SimpleHTTPRequestHandler):
    """SvelteKit SPA 静态服务器：

    1. 优先匹配文件
    2. 否则 fallback 到 index.html（SvelteKit 客户端路由需要）
    3. 防止路径穿越
    """

    def __init__(self, *args, directory: str | Path = None, **kwargs):
        super().__init__(*args, directory=str(directory), **kwargs)

    def send_head(self):
        """重写 SimpleHTTPRequestHandler.send_head 实现 SPA fallback"""
        # urlparse path → 去掉 query
        from urllib.parse import urlparse, unquote, parse_qs

        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # 防止路径穿越
        if ".." in path or path.startswith("//"):
            self.send_error(400, "invalid path")
            return None

        # 1. 优先匹配实际文件
        target = Path(self.directory) / path.lstrip("/")
        if target.is_file():
            return self._send_file(target)
        # 2. 目录：尝试 index.html
        if target.is_dir():
            idx = target / "index.html"
            if idx.is_file():
                return self._send_file(idx)
        # 3. SPA fallback：所有 GET 请求 → index.html（让 SvelteKit 客户端接管）
        index_path = Path(self.directory) / "index.html"
        if index_path.is_file():
            return self._send_file(index_path)
        # 4. 真的没有
        self.send_error(404, f"file not found: {path}")
        return None

    def _send_file(self, target: Path):
        """读文件按 mime 类型发送"""
        ctype = MIME_OVERRIDES.get(
            target.suffix,
            mimetypes.guess_type(str(target))[0] or "application/octet-stream",
        )
        try:
            body = target.read_bytes()
        except OSError:
            self.send_error(500, "read failed")
            return None
        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        # 返回非 None 让父类知道处理成功
        return target  # type: ignore[return-value]

    def log_message(self, fmt, *args):
        """静默默认 access log（dev-server.sh 自己 tail 日志）"""
        pass


def main():
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <port> <static_dir>", file=sys.stderr)
        sys.exit(1)

    port = int(sys.argv[1])
    static_dir = sys.argv[2]

    d = Path(static_dir).resolve()
    if not d.is_dir():
        print(f"static_dir not found: {d}", file=sys.stderr)
        sys.exit(1)

    handler_cls = partial(SpaHandler, directory=d)
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_cls)

    print(f"[spa_server] Serving {d} on http://0.0.0.0:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[spa_server] Shutting down", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    main()