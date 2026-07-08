"""
🆕 v1.7.28 输入验证器

设计目标：
  - 玩家输入"今日天气"等非游戏内容时，给出友好提示让重输
  - 但不能过度限制（不能把"我想了一下"判成非游戏内容）
  - 必须 fast（不能调 LLM，纯本地 + 关键字）

检测维度：
  1. 空输入 / 纯标点 / 纯英文
  2. 超出时代的"未来"概念（手机 / wifi / AI 等）
  3. 系统级指令（`/admin`, `SELECT *` 等）
  4. 与时代冲突的概念（"我是秦始皇"等）
  5. meta-query（"你怎么判断"等）
  6. 知识库查 0 条 + 关键词命中 < 阈值（提示但不阻断）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ============================================================
# 时代关键词表（万历年间）
# ============================================================

# 时代违和词（绝对拒绝 - 这些东西万历年间不存在）
ERA_FORBIDDEN_TERMS = [
    # 现代科技
    "手机", "电脑", "电话", "电视", "汽车", "火车", "飞机", "地铁",
    "wifi", "wi-fi", "互联网", "网络", "app", "微信", "支付宝",
    "ai", "人工智能", "机器人", "无人机", "互联网", "芯片", "电池",
    "电脑", "笔记本", "pad", "iphone", "android",
    # 现代概念
    "民主", "共和", "总统", "议会", "宪法", "共产", "社会主义",
    "资本主义", "帝国主义", "殖民", "金融", "股票", "期货",
    "比特币", "区块链", "元宇宙", "vr", "ar", "开挂",
    "公务员", "警察", "派出所", "法院", "律师",
    # 未来朝代/历史错误
    "清朝", "民国", "中华人民共和国", "日本投降", "解放",
    "康熙", "乾隆", "雍正", "嘉庆", "道光", "咸丰", "同治", "光绪", "宣统",
    "毛泽东", "孙中山", "蒋介石", "袁世凯",
    "我是秦始皇", "我是汉武帝", "我是唐太宗",
]

# 元查询词（玩家在问系统，不是在玩游戏）
META_QUERY_TERMS = [
    "你是谁", "你是什么", "你是ai", "你是机器人", "你是程序",
    "你怎么判断", "你的prompt", "你的system", "你的代码",
    "debug", "测试", "ignore previous", "ignore above",
    "system prompt", "system message", "ignore instructions",
    "请翻译", "translate", "help me",
    "this is a test",
    "show me the code", "give me the source",
]

# 元指令词（系统级命令）
META_COMMAND_PATTERNS = [
    re.compile(r"^\s*/\w+"),               # /admin, /save 等
    re.compile(r"^\s*SELECT\s+", re.I),     # SQL 注入
    re.compile(r"^\s*<script", re.I),       # XSS
    re.compile(r"^\s*javascript:", re.I),
    re.compile(r"^\s*drop\s+table", re.I),
    re.compile(r"^\s*eval\s*\(", re.I),
]

# 现代标点占主导
PUNCTUATION_ONLY = re.compile(r"^[\s\W_]+$", re.U)

# 纯英文（不含中文）
NO_CHINESE = re.compile(r"^[\x00-\x7f\s\W_]+$")


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool                                # 是否通过验证
    reason: Literal["ok", "empty", "meta_query", "era_violation",
                    "meta_command", "low_relevance", "too_long"] = "ok"
    message: str = ""                              # 友好提示（中文）
    suggestion: str = ""                           # 重输建议


# 友好提示文案
SUGGESTIONS = {
    "empty": "你似乎还没输入什么。要不要告诉我，此刻你想做些什么？",
    "meta_query": "我是 DM，只关心万历年间的故事。请告诉我你在这段历史里想做什么。",
    "era_violation": "这件事在万历年间并不存在。请换个跟时代相符的事情去做。",
    "meta_command": "系统指令无法在游戏中执行。请直接告诉我你的行动。",
    "low_relevance": "这似乎跟当前情境无关。请换个跟盛泽镇或你的角色有关的事。",
    "too_long": "你写的太多了。请控制在 200 字以内，言简意赅。",
}


def validate_input(
    text: str,
    *,
    max_length: int = 200,
    knowledge_matched: int = 0,
    knowledge_matched_required: int = 1,
) -> ValidationResult:
    """验证玩家输入

    Args:
        text: 玩家输入文本
        max_length: 最大长度（默认 200）
        knowledge_matched: 知识库匹配条数（0 = 没匹配）
        knowledge_matched_required: 最少需要匹配几条（默认 1）

    Returns:
        ValidationResult - 包含 is_valid / reason / message / suggestion
    """
    # ============================================================
    # 1. 空输入
    # ============================================================
    if not text or not text.strip():
        return ValidationResult(
            is_valid=False,
            reason="empty",
            message="你似乎还没输入什么",
            suggestion=SUGGESTIONS["empty"],
        )

    stripped = text.strip()

    # ============================================================
    # 2. 太长（可能是粘贴或恶意）
    # ============================================================
    if len(stripped) > max_length:
        return ValidationResult(
            is_valid=False,
            reason="too_long",
            message=f"内容超过 {max_length} 字",
            suggestion=SUGGESTIONS["too_long"],
        )

    # ============================================================
    # 3. 纯标点 / 纯英文 / 纯空白
    # ============================================================
    if PUNCTUATION_ONLY.match(stripped):
        return ValidationResult(
            is_valid=False,
            reason="empty",
            message="只有标点似乎不太够",
            suggestion=SUGGESTIONS["empty"],
        )

    if NO_CHINESE.match(stripped):
        return ValidationResult(
            is_valid=False,
            reason="meta_query",
            message="这是英文/符号，不是游戏内容",
            suggestion=SUGGESTIONS["meta_query"],
        )

    # ============================================================
    # 3.5 极短中文输入（1-2 字废话）
    # ============================================================
    # 1-2 字几乎都是废话（嗯/好/不/行/可以），但保留给"去！""走！"等行动
    # 判定条件：纯中文 + 长度 <= 2 + 不含"去/走/做/开/打/买/卖/织/想/说/看/听/问/要"
    if len(stripped) <= 2 and re.fullmatch(r"[\u4e00-\u9fa5]+", stripped):
        action_chars = "去做开打买卖织想说看听问要绣食查察寻赶冲回"
        if not any(c in action_chars for c in stripped):
            return ValidationResult(
                is_valid=False,
                reason="empty",
                message=f"「{stripped}」意思太模糊了",
                suggestion="请用完整的句子告诉我：你想做什么？",
            )

    # ============================================================
    # 4. 元指令（系统命令）
    # ============================================================
    for pattern in META_COMMAND_PATTERNS:
        if pattern.match(stripped):
            return ValidationResult(
                is_valid=False,
                reason="meta_command",
                message="系统指令无法在游戏中执行",
                suggestion=SUGGESTIONS["meta_command"],
            )

    # ============================================================
    # 5. 元查询（玩家在问系统问题）— 优先于时代违和
    # ============================================================
    for term in META_QUERY_TERMS:
        if term in stripped:
            return ValidationResult(
                is_valid=False,
                reason="meta_query",
                message=f"「{term}」是 meta 问题，不在游戏中",
                suggestion=SUGGESTIONS["meta_query"],
            )

    # ============================================================
    # 6. 时代违和词（东西万历年间不存在）
    # ============================================================
    lower_text = stripped.lower()
    for term in ERA_FORBIDDEN_TERMS:
        if term.lower() in lower_text:
            return ValidationResult(
                is_valid=False,
                reason="era_violation",
                message=f"「{term}」在万历年间并不存在",
                suggestion=SUGGESTIONS["era_violation"],
            )

    # ============================================================
    # 7. 知识库匹配度（软提示，不阻断）
    # ============================================================
    if knowledge_matched < knowledge_matched_required and len(stripped) >= 4:
        return ValidationResult(
            is_valid=True,
            reason="low_relevance",
            message="这似乎跟当前情境不太相关",
            suggestion=SUGGESTIONS["low_relevance"],
        )

    # ============================================================
    # 8. 通过验证
    # ============================================================
    return ValidationResult(is_valid=True, reason="ok")


def is_low_quality_input(text: str) -> bool:
    """快速判断：是否是低质量输入（前端可提前拦截）"""
    if not text or not text.strip():
        return True
    stripped = text.strip()
    if len(stripped) > 200:
        return True
    if PUNCTUATION_ONLY.match(stripped):
        return True
    if NO_CHINESE.match(stripped):
        return True
    return False
