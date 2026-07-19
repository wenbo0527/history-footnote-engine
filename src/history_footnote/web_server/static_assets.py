"""🆕 v2.10.10 静态资源加载

启动时一次性把 index.html 读进内存，路由分发时复用。

🆕 v2.10.10：切换至 SvelteKit 前端生产产物（src/frontend/build/）。
之前 v1.7.29 → v2.10.9 服务的是 src/history_footnote/web/templates/index.html
（v1.7.27 旧前端），但实际开发者用的是 src/frontend/ 的 SvelteKit 前端，导致
生产部署的 UI 错位 ~30 个版本。

现在统一：INDEX_HTML = src/frontend/build/index.html（build 时由 vite 生成）。
STATIC_DIR = src/frontend/static（命运卡 / 角色 / 场景图）。
"""

from __future__ import annotations

from pathlib import Path

# 🆕 v2.10.10：放弃 v1.7.27 旧 web/ 路径，统一指向 SvelteKit 生产产物。
# 这个常量以后是单一真实来源（single source of truth）。
# 计算路径：<repo>/src/history_footnote/web_server/static_assets.py
#               ↑ 4 层           ↑ 上溯到 src/frontend/
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
_FRONTEND_BUILD_DIR = _FRONTEND_DIR / "build"
_FRONTEND_STATIC_DIR = _FRONTEND_DIR / "static"

# 单一 INDEX_HTML：SvelteKit adapter-static 生成在 build/ 下
INDEX_HTML = (
    (_FRONTEND_BUILD_DIR / "index.html").read_text(encoding="utf-8")
    if (_FRONTEND_BUILD_DIR / "index.html").exists()
    else "<!-- SvelteKit build missing: cd src/frontend && npm run build -->"
)

# 向后兼容：保留旧符号（TEMPLATES_DIR / STATIC_DIR）但指向新位置
# - scripts/_archive/ 中有代码可能引用这些（虽然 .gitignore 已忽略）
TEMPLATES_DIR = _FRONTEND_BUILD_DIR
STATIC_DIR = _FRONTEND_STATIC_DIR

__all__ = ["INDEX_HTML", "TEMPLATES_DIR", "STATIC_DIR", "_FRONTEND_DIR",
           "_FRONTEND_BUILD_DIR", "_FRONTEND_STATIC_DIR"]


def frontend_paths_info() -> dict:
    """前端路径诊断（启动时调用，记入日志）

    Returns:
        dict: 路径信息，便于日志 / health check
    """
    return {
        "frontend_root": str(_FRONTEND_DIR),
        "build_dir": str(_FRONTEND_BUILD_DIR),
        "static_dir": str(_FRONTEND_STATIC_DIR),
        "index_html_exists": (_FRONTEND_BUILD_DIR / "index.html").exists(),
        "static_dir_exists": _FRONTEND_STATIC_DIR.exists(),
    }