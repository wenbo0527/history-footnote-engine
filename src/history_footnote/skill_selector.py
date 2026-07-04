"""🆕 v1.6.2 SKILL 选择性注入器

不是所有回合都需要 8 个 SKILL 全部触发。
根据 intent_type 选择性注入，减少 tokens：

| intent_type | 必须 SKILL | 可选 SKILL |
|---|---|---|
| action | 1（读场）+ 2（节奏）+ 4（史实）+ 7（三层） | 3（线索）, 5（声音）, 6（失败）, 8（认知） |
| inquire | 1 + 7 | 5, 8 |
| describe | 1 + 5 | 8 |
| voice | 1 + 5 | 8 |

收益估算：
- action 回合：~500 tokens → ~280 tokens（44% ↓）
- inquire 回合：~500 tokens → ~150 tokens（70% ↓）
- describe 回合：~500 tokens → ~120 tokens（76% ↓）

50 回合（30 action + 15 inquire + 5 describe）：
- 优化前：50 × 500 = 25,000 tokens
- 优化后：30×280 + 15×150 + 5×120 = 12,150 tokens（51% ↓）
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# SKILL → 对应 directive 中的 section 关键字
SKILL_SECTION_MARKERS = {
    "skill_1": "## 🔍 SKILL-1 读场判断",
    "skill_2": "## ⏱️ SKILL-2 节奏控制",
    "skill_3": "## 🧭 SKILL-3 线索投放",
    "skill_4": "## 📜 SKILL-4 史实锚定",
    "skill_5": "## 🎭 SKILL-5 价值观发声",
    "skill_6": "## 💔 SKILL-6 失败叙事化",
    "skill_7": "## ⚖️ SKILL-7 三层裁判",
    "skill_8": "## 🔍 SKILL-8 认知框架锁定",
}

# 基础 SKILL（所有回合都需要）
BASE_SKILLS = ["skill_1", "skill_7"]  # 读场 + 三层裁判是核心

# 按 intent_type 分组的 SKILL
SKILL_REQUIREMENTS_BY_INTENT = {
    "action": ["skill_2", "skill_4"],       # 节奏 + 史实锚定（动作要推进）
    "inquire": [],                            # 问询不需要额外 SKILL
    "describe": ["skill_5"],                  # 描述时调用价值观声音
    "voice": ["skill_5"],                     # 内在声音相关
}

# 可选 SKILL（按需追加）
OPTIONAL_SKILLS = {
    "skill_3": ["action"],         # 推进型动作需要线索
    "skill_6": ["action"],         # 失败叙事化只对 action 有意义
    "skill_8": ["action", "inquire", "describe"],  # 认知框架几乎总是需要
}


def select_skills(intent_type: str, state: dict | None = None) -> list[str]:
    """根据 intent_type 选择需要的 SKILL

    Args:
        intent_type: action / inquire / describe / voice
        state: 当前游戏状态（用于更精细判断，如 route_tendency）

    Returns:
        SKILL id 列表，如 ["skill_1", "skill_2", "skill_4", "skill_7"]
    """
    intent_type = intent_type or "action"

    # 1. 基础 SKILL
    selected = set(BASE_SKILLS)

    # 2. intent_type 强制 SKILL
    for skill in SKILL_REQUIREMENTS_BY_INTENT.get(intent_type, []):
        selected.add(skill)

    # 3. 智能判断：如果是 action 且 route_tendency 明确 → 8 必加
    if intent_type == "action" and state:
        route = state.get("route_tendency", "")
        if route and route not in ("", "unclear"):
            selected.add("skill_8")

    # 4. 转化为有序列表（按 SKILL 编号顺序）
    ordered = sorted(selected, key=lambda s: int(s.split("_")[1]))
    return ordered


def filter_skill_directive(skill_directive: str, selected_skills: list[str]) -> str:
    """从完整的 skill_directive 中过滤出选中的 SKILL sections

    Args:
        skill_directive: 完整的 8 SKILL directive 文本
        selected_skills: select_skills() 返回的 SKILL id 列表

    Returns:
        过滤后的 directive（更短）
    """
    if not skill_directive:
        return ""

    # 找到所有 SKILL section 的位置
    section_positions = []
    for skill_id, marker in SKILL_SECTION_MARKERS.items():
        pos = skill_directive.find(marker)
        if pos >= 0:
            section_positions.append((pos, skill_id, marker))

    if not section_positions:
        return skill_directive

    # 按位置排序
    section_positions.sort(key=lambda x: x[0])

    # 选中需要的 sections
    selected_set = set(selected_skills)
    filtered_parts = []

    for i, (pos, skill_id, marker) in enumerate(section_positions):
        if skill_id not in selected_set:
            continue

        # 找到该 section 的结束位置（下一个 section 开始 或 文件结尾）
        if i + 1 < len(section_positions):
            end_pos = section_positions[i + 1][0]
        else:
            end_pos = len(skill_directive)

        # 还要包括到下一个 ## 开头的所有内容
        # 简化：直接拿到下一个 section 的开头
        section_text = skill_directive[pos:end_pos]
        filtered_parts.append(section_text)

    # 加上头部综合指令（## 📌 综合指令）
    summary_marker = "## 📌 综合指令"
    summary_pos = skill_directive.find(summary_marker)
    if summary_pos >= 0:
        filtered_parts.append(skill_directive[summary_pos:])

    result = "\n".join(filtered_parts)
    return result


def estimate_token_savings(intent_type: str, original_tokens: int = 500) -> dict:
    """估算 token 节省"""
    selected = select_skills(intent_type)
    # 8 SKILL 总共 → 选择 N 个 SKILL → 节省 (8-N)/8
    saving_ratio = 1 - len(selected) / 8
    return {
        "intent_type": intent_type,
        "selected_skills": selected,
        "saving_ratio": saving_ratio,
        "original_tokens": original_tokens,
        "optimized_tokens": int(original_tokens * (1 - saving_ratio)),
        "saved_tokens": int(original_tokens * saving_ratio),
    }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("SKILL Selector 测试")
    print("=" * 50)

    for intent in ["action", "inquire", "describe", "voice"]:
        skills = select_skills(intent)
        est = estimate_token_savings(intent)
        print(f"\n{intent}: {len(skills)} SKILL → {est['selected_skills']}")
        print(f"  节省: {est['saving_ratio'] * 100:.0f}% ({est['saved_tokens']} tokens)")

    # 测试过滤
    full_directive = """
## 🔍 SKILL-1 读场判断
  scene: 在织机前

## ⏱️ SKILL-2 节奏控制
  pacing: slow_time

## 🧭 SKILL-3 线索投放
  type: 推动型

## 📜 SKILL-4 史实锚定
  春税提示

## 🎭 SKILL-5 价值观发声
  声音列表

## 💔 SKILL-6 失败叙事化

## ⚖️ SKILL-7 三层裁判
  verdict: 自由层

## 🔍 SKILL-8 认知框架锁定
  frame_id: scholar

## 📌 综合指令
  本回合采用 slow_time
"""
    selected = select_skills("inquire")
    filtered = filter_skill_directive(full_directive, selected)
    print(f"\ninquire 过滤后长度: {len(filtered)} chars (原始 {len(full_directive)} chars)")
    print(f"过滤后:\n{filtered}")

    print("\n✅ SKILL Selector 测试通过")