"""🆕 v2.10.10 web_server CLI 入口

让 `python -m history_footnote.web_server` 能直接跑（带可选参数）：
- 默认监听 0.0.0.0:8765
- `--host` / `--port` 覆盖
- `--mock` / `--check` / `--show-frontend` 几个调试子命令

为什么单独文件：
- `__init__.py` 不适合做 CLI 入口（import 时会执行 setup）
- package + `__main__.py` 是 Python 官方推荐方式
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """CLI 入口

    用法：
        python -m history_footnote.web_server                 # 默认启动
        python -m history_footnote.web_server --port 9000     # 自定义端口
        python -m history_footnote.web_server --host 127.0.0.1
        python -m history_footnote.web_server --show-frontend # 打印前端路径诊断
    """
    parser = argparse.ArgumentParser(
        prog="history_footnote.web_server",
        description="🆕 v2.10.10 历史注脚 web_server (单进程 API + SvelteKit 前端)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听 host (默认 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听 port (默认从 history_footnote.config.Server.DEFAULT_PORT 读)",
    )

    # ==================== 调试子命令 ====================
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--show-frontend",
        action="store_true",
        help="打印前端路径诊断（build_dir / static_dir / index_html_exists）并退出",
    )
    g.add_argument(
        "--check",
        action="store_true",
        help="只检查启动可行性（import + 路径诊断），不真的启动 server",
    )

    args = parser.parse_args(argv)

    # ==================== show-frontend ====================
    if args.show_frontend:
        try:
            from history_footnote.web_server.static_assets import frontend_paths_info
            import json

            info = frontend_paths_info()
            print(json.dumps(info, ensure_ascii=False, indent=2))
            # 简单状态码
            if not info["index_html_exists"]:
                print("\n⚠️  SvelteKit build 缺失", file=sys.stderr)
                print("   修复方法: cd src/frontend && npm run build", file=sys.stderr)
                return 1
            return 0
        except Exception as e:
            print(f"前端诊断失败: {e}", file=sys.stderr)
            return 2

    # ==================== check / import-test ====================
    if args.check:
        # 已经能 import 走到这里 = OK
        print("✅ web_server 可正常 import")
        try:
            from history_footnote.web_server.static_assets import frontend_paths_info
            info = frontend_paths_info()
            print(f"   build_dir: {info['build_dir']}")
            print(f"   index_html_exists: {info['index_html_exists']}")
            print(f"   static_dir_exists: {info['static_dir_exists']}")
        except Exception as e:
            print(f"   （frontend 诊断失败: {e}）")
        return 0

    # ==================== 默认启动 ====================
    # 动态 import 避免顶层失败时也有 --show-frontend / --check 能用
    from history_footnote.web_server import run

    # port 默认值：从 config 读
    if args.port is None:
        try:
            from history_footnote.config import Server
            port = Server.DEFAULT_PORT
        except Exception:
            port = 8765
    else:
        port = args.port

    host = args.host
    print(f"🆕 v2.10.10 启动 web_server @ {host}:{port}（单进程 API + SvelteKit 前端）", flush=True)
    run(host=host, port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())