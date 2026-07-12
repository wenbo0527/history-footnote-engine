"""🆕 v2.10.1 W52 P1-1 followup 辅助脚本：把 event_parser.py 拆出 event_handlers.py

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-1 followup
- event_parser.py 655 行 → 主模块只保留解析 + 入口 + 模糊匹配
- event_handlers.py 新建 325 行 → 8 个 _apply_xxx 处理器
"""
from pathlib import Path

src_path = Path("src/history_footnote/event_parser.py")
lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

# 提取 8 个 _apply_xxx 处理器（行 89-415）
handlers_block = "".join(lines[88:415])

# 新建 event_handlers.py
new_handlers = f'''"""🆕 v2.10.1 W52 P1-1 followup: 事件处理器模块

把 event_parser.py 8 个 _apply_xxx 处理器拆出,主模块只保留:
- 解析(parse_events)
- 入口(apply_event / process_llm_output)
- 模糊匹配(Layer 2)

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-1 followup
"""
from __future__ import annotations

from typing import Any, Callable

# 🆕 命名空间常量（从 event_parser 复用）
FIN_EVENTS = {{
    "sell_silk", "buy_thread", "pay_tax", "borrow", "repay",
    "deposit_interest", "debt_interest", "workshop_rent",
    "monthly_burn", "gift_in", "gift_out",
}}

CITY_IDS = {{"shengze", "suzhou", "hangzhou", "songjiang", "nanjing"}}

FAM_STATUSES = {{"healthy", "sick", "recovering", "dying", "deceased"}}


def _log(logger, msg: str) -> None:
    """统一日志入口"""
    if logger:
        logger.warning(msg)


{handlers_block}

__all__ = ["_HANDLERS", "FIN_EVENTS", "CITY_IDS", "FAM_STATUSES"]
'''

Path("src/history_footnote/event_handlers.py").write_text(new_handlers, encoding="utf-8")
print(f"✓ event_handlers.py created ({len(new_handlers.splitlines())} lines)")

# 修改 event_parser.py：删 89-415 + 删 _log + 加 import
# 保留行 1-83（到 _log 之前的 def apply_event 结束）
# 删 84-415（_log + 处理器 + HANDLERS dict）
# 加 import event_handlers
# 续 416+ 内容

new_parser = (
    "".join(lines[:83])  # 行 1-83
    + "\n\n# 🆕 v2.10.1 W52 P1-1 followup: 处理器已拆到 event_handlers.py\n"
    "from history_footnote.event_handlers import _HANDLERS, _log, FIN_EVENTS, CITY_IDS, FAM_STATUSES\n\n"
    + "".join(lines[415:])  # 行 416+
)
src_path.write_text(new_parser, encoding="utf-8")
print(f"✓ event_parser.py updated ({len(new_parser.splitlines())} lines, was {len(lines)})")
