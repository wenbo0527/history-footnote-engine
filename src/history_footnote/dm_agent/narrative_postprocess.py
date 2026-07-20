"""🆕 v2.10.1 W52 候选 E: dm_agent/narrative_postprocess.py

从 agent.py:485-547 抽出 narrative 后处理逻辑：
- 长度/问号/字数检查
- 重试循环（最多 2 次）
- 截断兜底

为什么拆出：
- agent.py 719 行过大（核心是 graph 编排，不是后处理）
- 独立测试：测试后处理逻辑不需要 LLM/graph

历史：
- v1.7.30 P1-⑤ 把 make_tools 等从 dm_agent.py 拆出
- v2.10.1 W52 进一步拆 run/regenerate 共享的 narrative 后处理
"""
from __future__ import annotations

import logging
from typing import Callable

_log = logging.getLogger("history_footnote")


# 🆕 v2.3 字数约束（按时间模式，详见 system_base.md "字数控制" 章节）
MAX_CHARS_BY_MODE = {
    "abstract_time": 180,
    "sharp_cut":     320,
    "now_time":      500,
    "slow_time":     700,
}

DEFAULT_CHAR_LIMIT = 800


def _narr_ends_with_question(text: str) -> bool:
    """narrative 末尾 30 字内是否含问号（?/？）"""
    if not text:
        return False
    tail = text[-30:].strip()
    return ("?" in tail) or ("？" in tail)


def _truncate_to_sentence(narrative: str, char_limit: int) -> str:
    """截断 narrative 到 char_limit 的 80%，在最近的句号处切断"""
    if len(narrative) <= char_limit:
        return narrative
    cut_at = int(char_limit * 0.8)
    for i in range(cut_at, min(cut_at + 50, len(narrative))):
        if narrative[i] in "。！？\n":
            return narrative[:i+1]
    return narrative[:cut_at] + "……"


def check_narrative_quality(narrative: str, time_mode: str = "now_time") -> tuple[bool, str]:
    """检查 narrative 质量

    Returns:
        (need_retry, reason)
    """
    char_limit = MAX_CHARS_BY_MODE.get(time_mode, DEFAULT_CHAR_LIMIT)
    if len(narrative) < 100:
        return True, f"短答（{len(narrative)}字）"
    if len(narrative) > char_limit:
        return True, f"过长（{len(narrative)}>{char_limit}字，{time_mode}模式）"
    if not _narr_ends_with_question(narrative):
        return True, "末尾无问号"
    return False, ""


def postprocess_narrative(
    narrative: str,
    time_mode: str,
    retry_fn: Callable[[], str] | None = None,
    max_retries: int = 2,
) -> tuple[str, str]:
    """后处理 narrative：检查 / 重试 / 截断

    Args:
        narrative: 初始 narrative
        time_mode: 时间模式（决定字数上限）
        retry_fn: 重试函数（无参，返回新 narrative）
        max_retries: 最大重试次数

    Returns:
        (final_narrative, status)
        status: "ok" / "retried_success" / "truncated"
    """
    char_limit = MAX_CHARS_BY_MODE.get(time_mode, DEFAULT_CHAR_LIMIT)

    # 🆕 v2.10.12+: 防御 narrative 是 list/None 等非 str 类型
    # (LLM 偶尔返回 list，特别是 tool_use content 字段)
    if not isinstance(narrative, str):
        try:
            narrative = str(narrative) if narrative is not None else ""
        except Exception:
            narrative = ""

    # 1. 检查
    need_retry, reason = check_narrative_quality(narrative, time_mode)
    if not need_retry:
        return narrative, "ok"

    _log.warning(f"[v2.3] narrative {reason}，触发重试")

    # 2. 重试
    if retry_fn is not None:
        for retry_i in range(max_retries):
            try:
                _retry_narr = retry_fn()
                # 🆕 v2.10.12+: 防御 retry_fn 返回 list
                if not isinstance(_retry_narr, str):
                    try:
                        _retry_narr = str(_retry_narr) if _retry_narr is not None else ""
                    except Exception:
                        _retry_narr = ""
                narrative = _retry_narr
                need_retry, _ = check_narrative_quality(narrative, time_mode)
                if not need_retry:
                    _log.info(
                        f"[v2.3] 第 {retry_i+1} 次重试成功，narrative={len(narrative)}字"
                    )
                    return narrative, "retried_success"
            except Exception as e:
                _log.exception(f"[v2.3] 重试 {retry_i+1} 失败: {e}")
                break

    # 3. 截断兜底
    _log.warning(
        f"[v2.3] {max_retries} 次重试仍失败，narrative={len(narrative)}字（目标≤{char_limit}）"
    )
    truncated = _truncate_to_sentence(narrative, char_limit)
    if truncated != narrative:
        _log.warning(f"[v2.3] 已截断 narrative 到 {len(truncated)}字")
        return truncated, "truncated"
    return narrative, "truncated"
