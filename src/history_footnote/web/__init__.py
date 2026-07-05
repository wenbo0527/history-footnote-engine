"""🆕 v1.7.3 Web 子包

将原 3377 行的 web_server.py 拆分：
- server.py      路由 + 启动（Handler 类）
- static/css/    独立 CSS 文件
- static/js/     独立 JS 文件
- templates/     HTML 模板

模块设计原则：
- 路由逻辑在 web_server.py（保持原入口）
- 静态文件通过 /static/ 路径提供
- 模板在 templates/ 单独管理
"""
from pathlib import Path

# 子包路径常量
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


__all__ = ["WEB_DIR", "STATIC_DIR", "TEMPLATES_DIR", "CSS_DIR", "JS_DIR"]
