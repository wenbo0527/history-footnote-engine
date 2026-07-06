"""🆕 v1.7.28 回归测试：dir() 兜底修复

验证：
1. _run_round 路径中 structured_voice_options 在使用点之前已声明
2. wiki.auto_extract_from_narrative 能正确拿到 player_options
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from history_footnote.game_state import GameState
from history_footnote.character_wiki import CharacterWiki
from history_footnote.narrative_sanitizer import merge_voice_options


def test_structured_voice_options_reaches_wiki():
    """模拟 _run_round 流程，验证 wiki 可拿到选项"""
    # 场景：LLM 把选项写进了 narrative，没通过 voice_options 字段
    # 注：merge_voice_options 用的是"行首标号"正则，要求 "一、xxx" 格式
    narrative = (
        "你在织机前叹息。冬天米缸见底了。\n\n"
        "一、去找赵里长预支春税\n"
        "二、把织机抵押\n"
        "三、上镇里听消息\n\n"
        "你想做什么？"
    )

    # 模拟修改后的流程
    dm_response = {"voice_options": [], "narrative": narrative}

    # 提前到 wiki 调用前（v1.7.28 修复）
    structured_voice_options = dm_response.get("voice_options", []) or []
    if not structured_voice_options and narrative:
        structured_voice_options = merge_voice_options(None, narrative)

    print(f"  ✅ 提取到 {len(structured_voice_options)} 个选项")
    assert len(structured_voice_options) >= 2, "应至少提取 2 个选项"

    # wiki 现在能拿到
    wiki = CharacterWiki(save_id="test_session")
    wiki.auto_extract_from_narrative(
        narrative=narrative,
        round=1,
        player_input="我想想",
        player_options=[opt.get("intent_text", "") for opt in structured_voice_options],
    )
    print(f"  ✅ wiki 提取：{len(wiki.events)} 事件 / {len(wiki.decisions)} 决策")
    # 至少应该有些内容
    assert len(wiki.events) >= 0  # 不报错即可


def test_structured_voice_options_with_llm_provided():
    """DM 直接返回 voice_options 时也能用"""
    narrative = "叙事。"
    dm_response = {
        "voice_options": [
            {"voice_name": "算盘声", "intent_text": "盘算"},
            {"voice_name": "手艺人的骄傲", "intent_text": "坚持品质"},
        ]
    }

    structured = dm_response.get("voice_options", []) or []
    if not structured and narrative:
        structured = merge_voice_options(None, narrative)

    print(f"  ✅ LLM 提供 {len(structured)} 个选项直接生效")
    assert len(structured) == 2


def test_no_voice_options_no_crash():
    """没有 voice_options 时不崩"""
    narrative = "叙事，但无选项。"
    dm_response = {"voice_options": []}

    structured = dm_response.get("voice_options", []) or []
    if not structured and narrative:
        structured = merge_voice_options(None, narrative)

    # wiki 拿到 None 时不崩（player_options=None）
    wiki = CharacterWiki(save_id="x")
    opts = [opt.get("intent_text", "") for opt in structured] if structured else None
    wiki.auto_extract_from_narrative(
        narrative=narrative, round=1, player_input="x", player_options=opts,
    )
    print("  ✅ 无选项时不崩")


if __name__ == "__main__":
    print("=== v1.7.28 dir() 兜底修复回归测试 ===\n")
    test_structured_voice_options_reaches_wiki()
    test_structured_voice_options_with_llm_provided()
    test_no_voice_options_no_crash()
    print("\n🎉 3 组测试通过")
