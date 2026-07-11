"""v2.7.2 NarrativeFactExtractor 单元测试（不调 LLM，只测 fallback + schema + 注入）"""
import sys
import os
import json
from pathlib import Path

# 确保 import 路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.narrative_facts_extractor import (
    NarrativeFact,
    extract_facts_from_narrative,
    _fallback_extract,
    _parse_json_from_text,
    build_facts_injection,
    FACT_TYPES,
    MAX_FACTS_PER_SAVE,
)


def test_fact_schema():
    """测试 dataclass ↔ dict 转换"""
    f = NarrativeFact(
        type="character",
        content="沈氏是玩家妻子",
        key="shen_wife",
        round=1,
        importance=9,
    )
    d = f.to_dict()
    assert d["type"] == "character"
    assert d["content"] == "沈氏是玩家妻子"
    assert d["key"] == "shen_wife"
    assert d["importance"] == 9
    f2 = NarrativeFact.from_dict(d)
    assert f2.type == f.type
    assert f2.importance == f.importance
    print("✅ test_fact_schema")


def test_fallback_extract_basic():
    """测试 fallback 启发式提取（你贴的回合 0/1 narrative）"""
    narrative_0 = """万历十五年，正月。清晨的盛泽镇还笼着一层薄雾，你推开作坊的门，冷气扑面而来。两台织机安静地蹲在昏暗的屋子里，像两头沉睡的牲口。
    灶房里传来沈氏生火的声音，锅铲碰着铁锅，叮叮当当。隔壁张寡妇家的织机已经响了起来——她总是起得最早。
    沈氏说："当家的，让孩子去试试吧。"
    阿宝从后院跑出来，手里攥着半块年糕："爹，先生说明天开课了，要交束脩。"
    你摸了摸他的头，没说话。束脩二两银子，加上春税预单，加上买桑叶的定钱……
    赵里长昨天托人带话，说今天要来收春税的预单。"""
    facts = _fallback_extract(narrative_0, round_num=0)
    assert len(facts) > 0, "fallback 至少要提取 1 条"
    # 至少 1 个 NPC
    npc_facts = [f for f in facts if f.type == "character"]
    assert len(npc_facts) >= 1, f"应该提取至少 1 个 NPC，实际 {len(npc_facts)}"
    # 验证 NPC 名（沈氏/张寡妇/阿宝 至少 1 个）
    contents = " ".join(f.content for f in npc_facts)
    assert any(n in contents for n in ["沈氏", "张寡妇", "阿宝"]), f"NPC 不对: {contents}"
    # 末尾问号（未解）应该被提取
    open_q = [f for f in facts if f.type == "open_question"]
    # 末尾没问号时不应该强加
    print(f"   提取 {len(facts)} 条 fact:")
    for f in facts:
        print(f"   - [{f.type}] {f.content} (key={f.key}, imp={f.importance})")
    print("✅ test_fallback_extract_basic")


def test_fallback_extract_with_question():
    """测试末尾有问号时的 open_question 提取"""
    narrative = """灶房里的水开了，咕嘟咕嘟地响。远处牙行的算盘声噼里啪啦传过来。
    阿宝站在门口，等你回答。阿宝说："李先生会不会……不要我？"
    二两银子的事，现在压在一个八岁孩子的肩膀上。
    接下来怎么办？"""
    facts = _fallback_extract(narrative, round_num=1)
    open_q = [f for f in facts if f.type == "open_question"]
    assert len(open_q) >= 1, f"末尾有问号时应该提取 open_question，实际 {len(open_q)}"
    print(f"   open_question: {open_q[0].content}")
    print("✅ test_fallback_extract_with_question")


def test_parse_json_from_text():
    """测试从 LLM 输出抠 JSON"""
    # 情况 1: ```json 包裹
    t1 = '```json\n{"facts": [{"type": "character", "content": "x", "key": "k", "importance": 8}]}\n```'
    d1 = _parse_json_from_text(t1)
    assert d1 is not None
    assert "facts" in d1
    assert len(d1["facts"]) == 1

    # 情况 2: 纯文本中夹 JSON
    t2 = '思考中... \n{"facts": [{"type": "fact", "content": "y", "key": "k2", "importance": 7}]}\n结束'
    d2 = _parse_json_from_text(t2)
    assert d2 is not None
    assert d2["facts"][0]["content"] == "y"

    # 情况 3: 错误 JSON
    t3 = "no json here"
    d3 = _parse_json_from_text(t3)
    assert d3 is None

    print("✅ test_parse_json_from_text")


def test_build_facts_injection_grading():
    """测试分级注入（always vs relevant）"""
    facts = [
        NarrativeFact(type="character", content="沈氏是玩家妻子", key="shen_wife", importance=9),
        NarrativeFact(type="fact", content="阿宝束脩要二两银子", key="tuition", importance=9),
        NarrativeFact(type="hook", content="赵里长今天来收税", key="tax_today", importance=8),
        NarrativeFact(type="open_question", content="要不要让阿宝去念书", key="ah_bao", importance=8),
    ]
    out = build_facts_injection(facts, max_always=10, max_relevant=3)
    assert "人物 / 事实" in out
    assert "沈氏是玩家妻子" in out
    assert "阿宝束脩要二两银子" in out
    assert "伏笔 / 未解" in out
    assert "赵里长" in out
    print("✅ test_build_facts_injection_grading")
    print("   --- 注入文本（前 400 字）---")
    print(out[:400])


def test_extract_facts_no_llm():
    """不传 llm，应该走 fallback"""
    narrative = "沈氏说：'当家的，让孩子去试试。' 阿宝攥着年糕，紧张地看着你。明天怎么办？"
    facts = extract_facts_from_narrative(narrative, round_num=1, llm_wrapper=None)
    assert len(facts) > 0
    print(f"✅ test_extract_facts_no_llm: 提取 {len(facts)} 条")


def test_fact_types_constant():
    """验证 FACT_TYPES 是 4 类"""
    assert set(FACT_TYPES) == {"character", "fact", "hook", "open_question"}
    print(f"✅ test_fact_types_constant: {FACT_TYPES}")


def test_gamestate_append_facts():
    """测试 GameState.append_facts / get_facts_for_prompt / 去重 / 上限"""
    from history_footnote.game_state import GameState

    gs = GameState()
    assert len(gs.narrative_facts) == 0

    # 追加 3 条
    gs.append_facts([
        {"type": "character", "content": "A", "key": "a", "importance": 9, "round": 1},
        {"type": "fact", "content": "B", "key": "b", "importance": 7, "round": 1},
        {"type": "hook", "content": "C", "key": "c", "importance": 8, "round": 1},
    ])
    assert len(gs.narrative_facts) == 3

    # 同 key 替换
    gs.append_facts([
        {"type": "character", "content": "A_updated", "key": "a", "importance": 10, "round": 2},
    ])
    assert len(gs.narrative_facts) == 3, "去重应该不增加条数"
    a_fact = next(f for f in gs.narrative_facts if f["key"] == "a")
    assert a_fact["content"] == "A_updated"
    assert a_fact["round"] == 2

    # get_facts_for_prompt 按 importance 倒序
    sorted_facts = gs.get_facts_for_prompt()
    assert sorted_facts[0]["importance"] == 10
    print(f"✅ test_gamestate_append_facts: 3 条，a 被替换为 importance=10")


if __name__ == "__main__":
    test_fact_schema()
    test_fallback_extract_basic()
    test_fallback_extract_with_question()
    test_parse_json_from_text()
    test_build_facts_injection_grading()
    test_extract_facts_no_llm()
    test_fact_types_constant()
    test_gamestate_append_facts()
    print("\n🎉 全部 8 项测试通过")
