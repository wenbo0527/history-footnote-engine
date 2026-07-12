"""🆕 v2.10.1 W52 P1-2 PR#1: GameLoop 显示函数模块

把 GameLoop 类中 5 个纯显示函数（无状态读写副作用）拆出：
- print_opening(state, era_config, identity_config, era_id, selected_identity)
- display_narrative(narrative)
- display_state(state)
- display_full_state(session, state, memory)
- help_text()

GameLoop 类中保留同名方法作为 thin wrapper（向后兼容，零行为变化）。

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def print_opening(
    state,
    era_config: dict,
    identity_config: dict,
    era_id: str,
    selected_identity: str,
) -> None:
    """打印开场白——根据身份动态变化

    v1.5.1+：如果 state.custom_character 存在（玩家在 8 步向导中由 LLM 生成的人设），
    优先使用人设的开场白。
    """
    era_name = era_config.get("era_name", "")
    gender_label = "♂" if state.player_gender == "male" else "♀" if state.player_gender == "female" else ""
    label = identity_config.get("label", "小人物")
    role = identity_config.get("role", "小人物")
    description = identity_config.get("description", "你是这个时代的一个小人物。")

    # 🐛 v1.5.1 P0 Bug #1 修复：优先用 custom_character
    cc = getattr(state, "custom_character", None)
    cc_has_narrative = cc and (
        cc.get("opening_paragraph") or cc.get("background") or cc.get("starting_situation")
    )
    if cc and cc_has_narrative:
        # 🆕 v1.9.5 修复：去掉装饰性 "==========" 字符
        print(f"\n欢迎来到【{era_name}】 {gender_label}")
        print(f"\n你是 {cc.get('name', '?')} — {cc.get('hometown', '盛泽镇')}")
        if cc.get('family'):
            family_str = ' / '.join([f"{k}: {v}" for k, v in list(cc.get('family', {}).items())[:3]])
            if family_str:
                print(f"家庭：{family_str}")
        if cc.get('background'):
            print(f"\n【来历】{cc['background']}")
        if cc.get('starting_situation'):
            print(f"\n【开局处境】{cc['starting_situation']}")
        if cc.get('opening_paragraph'):
            print(f"\n{cc['opening_paragraph']}")
        print(f"\n日期：{state.current_date}\n")
        return

    # 优先从dm_persona.md的开场白部分读
    is_default_identity = selected_identity == era_config.get("world", {}).get("default_identity", "")

    if not is_default_identity or not has_persona_opening(era_id):
        # 🆕 v1.9.5 修复
        print(f"\n欢迎来到【{era_name}】 {gender_label}")
        print(f"\n你选择成为：{label}")
        print(f"你的身份：{role}")
        print(f"\n{description}")
        print(f"\n日期：{state.current_date}\n")
    else:
        opening = get_persona_opening(era_id)
        print(f"\n{opening}\n")


def has_persona_opening(era_id: str) -> bool:
    """检查dm_persona.md是否有开场白"""
    persona_path = Path("eras") / era_id / "dm_persona.md"
    if not persona_path.exists():
        return False
    text = persona_path.read_text(encoding="utf-8")
    return "# 开场白" in text


def get_persona_opening(era_id: str) -> Optional[str]:
    """从dm_persona.md提取开场白（返回 raw text 头部）"""
    persona_path = Path("eras") / era_id / "dm_persona.md"
    if not persona_path.exists():
        return None
    text = persona_path.read_text(encoding="utf-8")
    if "# 开场白" not in text:
        return None
    # 取 # 开场白 之后的内容
    after = text.split("# 开场白", 1)[1]
    # 找下一个 # 标题(若有)
    lines = after.split("\n")
    body_lines = []
    for line in lines:
        if line.startswith("# ") and body_lines:
            break
        body_lines.append(line)
    return "\n".join(body_lines).strip() or None


def display_narrative(narrative: str) -> None:
    """展示叙事"""
    print(f"\n【DM叙事】\n{narrative}")


def display_state(state) -> None:
    """展示状态"""
    visible = state.get_visible_state()
    ap_cur = visible.get('action_points_current', 0)
    ap_max = visible.get('action_points_max', 3)
    ap_bar = "●" * ap_cur + "○" * (ap_max - ap_cur)
    print(f"\n[状态] 回合{visible['round']} | {visible['date']} | 行动点 {ap_bar} {ap_cur}/{ap_max} | 已解锁认知{visible['unlocked_insights_count']}个")


def display_full_state(session, state, memory) -> None:
    """展示完整状态"""
    print(f"\n{'=' * 40}")
    print(f"会话: {session.session_id}")
    print(f"回合: {state.round_number} | 日期: {state.current_date}")
    print(f"{'=' * 40}")
    print("\n变量:")
    for k, v in state.variables.items():
        print(f"  {k}: {v:.1f}")
    print(f"\n已触发事件: {len(state.triggered_events)}")
    print(f"已解锁认知: {state.unlocked_insights}")
    print(f"NPC关系: {state.npc_levels}")
    print(f"价值观: {state.value_shifts}")
    print(f"事件日志: {memory.count()}条")
    print(f"\n存档:")
    for name, slot in session.slots.items():
        print(f"  {name}: 回合{slot.round_number} {slot.current_date}")
    print(f"{'=' * 40}\n")


def help_text() -> str:
    """返回帮助文本（无状态）"""
    return """
可用元指令：
  /state         - 查看完整游戏状态
  /save [1|2|3]  - 保存到slot1/2/3（不传则存slot1）
  /load [1|2|3|auto] - 从指定slot读档
  /quit          - 退出游戏
  /help          - 显示帮助

游戏玩法：
  直接输入你想做的任何事（去牙行、问税收、织丝绸等）
  DM会根据时代背景和你的行动生成叙事

存档机制：
  - 每回合结束自动存档（auto.json）
  - 手动存档有3个slot（slot1/2/3.json）
  - 重新游戏用：python -m history_footnote continue
  - 列出存档：python -m history_footnote list-saves
"""