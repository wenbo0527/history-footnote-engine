"""🆕 v1.7.29 静态资源加载

启动时一次性把 index.html 读进内存，路由分发时复用。
"""
from __future__ import annotations

from pathlib import Path

from history_footnote.web import TEMPLATES_DIR as _TPL_DIR

_INDEX_HTML_PATH = _TPL_DIR / "index.html"
INDEX_HTML = (
    _INDEX_HTML_PATH.read_text(encoding="utf-8")
    if _INDEX_HTML_PATH.exists()
    else "<!-- template missing -->"
)
