"""🆕 v1.9.5 测试：initial_state_resolver + format_state 集成

测试场景：
1. 中文数字解析（"一两二钱" → 1.2, "三两" → 3.0）
2. extract_initial_state_from_character 纯文本正则解析
3. extract_initial_state_from_character LLM initial_state 字段优先
4. extract_initial_state_from_character identity_config.base_state 兜底
5. apply_initial_state 写入 GameState
6. format_state 输出 character 顶层字段
7. 端到端：用户给出的"沈织户"narrative → state.cash=1.2, debt=3.0, family=[张氏,大毛,母亲]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def test_chinese_number_parser():
    from history_footnote.initial_state_resolver import parse_chinese_number
    cases = [
        ("1.2", 1.2),
        ("3", 3.0),
        ("一两", 1.0),
        ("一两二钱", 1.2),
        ("三两", 3.0),
        ("四钱二分", 0.42),
        ("八钱", 0.8),
        ("半两", 0.5),
        ("十二两", 12.0),
        ("二十两", 20.0),
        ("一百两", 100.0),
    ]
    for s, expected in cases:
        got = parse_chinese_number(s)
        ok = (got is not None and abs(got - expected) < 0.01) or (got is None and expected is None)
        status = "✅" if ok else "❌"
        print(f"{status} parse_chinese_number({s!r}) = {got} (期望 {expected})")
        assert ok, f"FAIL: {s!r} → {got}, expected {expected}"


def test_extract_from_text_only():
    """场景：用户提供的 narrative 文本，没有 LLM 初始 state"""
    from history_footnote.initial_state_resolver import extract_initial_state_from_character
    cc = {
        "name": "沈织户",
        "age": 30,
        "background": "沈家原也不是盛泽本地人，正德年间祖上从嘉兴府桐乡逃水患过来，在盛泽镇东巷子买了这两间屋子、置了一台旧织机，从此落脚。传到沈织户手里，织机是两台，欠着绸缎牙行周二爷三两银子的旧账，去年添丁没添进，反倒赔了一台机子的经钱。母亲张氏本是邻村张裁缝的闺女，嫁过来十六年，眼睛是生孩子时落下的病。",
        "starting_situation": "手头现银一两二钱，欠牙行周二爷三两（利息每月三分），上月赊的桑叶钱八钱还没结。马上要交春税折银（合四钱二分），大毛束脩下月也该续了。",
        "family": {
            "mother": "张氏（58岁）",
            "wife": "张氏（26岁）",
            "son": "大毛（5岁）",
        },
    }
    identity_config = {
        "base_state": {
            "cash": 1.2, "debt": 3.0, "rice": 0.0, "monthly_burn": 0.42,
        }
    }
    result = extract_initial_state_from_character(cc, identity_config)
    print(f"\n[测试1] 纯文本 + base_state 兜底")
    print(f"  source = {result['source']}")
    print(f"  cash = {result['cash']}, debt = {result['debt']}, monthly_burn = {result['monthly_burn']}")
    print(f"  family_members = {len(result['family_members'])}")
    print(f"  active_tasks = {len(result['active_tasks'])}")
    print(f"  upcoming_deadlines = {len(result['upcoming_deadlines'])}")

    assert result["cash"] == 1.2, f"cash should be 1.2, got {result['cash']}"
    assert result["debt"] == 3.0, f"debt should be 3.0, got {result['debt']}"
    assert abs(result["monthly_burn"] - 0.42) < 0.01, f"monthly_burn should be ~0.42, got {result['monthly_burn']}"
    assert len(result["family_members"]) == 3, f"family should be 3 (mother, wife, son), got {len(result['family_members'])}"
    # 家庭成员名字验证
    family_names = [m["name"] for m in result["family_members"]]
    assert "张氏" in family_names or any("张氏" in n for n in family_names), f"张氏 should be in family, got {family_names}"
    assert "大毛" in family_names or any("大毛" in n for n in family_names), f"大毛 should be in family, got {family_names}"
    # 任务应该有"还牙行账"或"束脩"
    task_titles = [t["title"] for t in result["active_tasks"]]
    assert any("还" in t or "束脩" in t for t in task_titles), f"应该有还账/束脩任务, got {task_titles}"
    # 还债日应该有牙行利息或春税
    deadline_names = [d["name"] for d in result["upcoming_deadlines"]]
    assert any("牙行" in n or "春税" in n for n in deadline_names), f"应该有牙行/春税还债, got {deadline_names}"
    print("  ✅ 全部通过")


def test_llm_struct_priority():
    """场景：LLM 返回了 initial_state 结构化字段，应该优先于文本解析"""
    from history_footnote.initial_state_resolver import extract_initial_state_from_character
    cc = {
        "name": "沈织户",
        "background": "（文本）",
        "starting_situation": "（文本）",
        "initial_state": {
            "cash": 5.0,  # 与文本不一致，优先用这个
            "debt": 2.0,
            "family_members": [
                {"id": "fm_x", "name": "测试妻", "relation": "wife", "age": 25, "location": "shengze", "alive": True, "notes": ""}
            ],
            "active_tasks": [
                {"title": "测试任务", "urgency": "high", "status": "pending"}
            ],
        }
    }
    result = extract_initial_state_from_character(cc, {})
    print(f"\n[测试2] LLM initial_state 字段优先")
    print(f"  source = {result['source']}")
    assert result["cash"] == 5.0, f"cash should be 5.0 (from LLM struct), got {result['cash']}"
    assert result["debt"] == 2.0, f"debt should be 2.0, got {result['debt']}"
    assert len(result["family_members"]) == 1, f"family should be 1 (from LLM), got {len(result['family_members'])}"
    assert result["family_members"][0]["name"] == "测试妻", f"got {result['family_members'][0]}"
    assert result["source"] == "llm_struct", f"source should be llm_struct, got {result['source']}"
    print("  ✅ 全部通过")


def test_base_state_fallback():
    """场景：完全没 cc → 用 identity_config.base_state 兜底"""
    from history_footnote.initial_state_resolver import extract_initial_state_from_character
    identity_config = {
        "base_state": {
            "cash": 7.5,
            "debt": 1.0,
            "rice": 2.0,
            "monthly_burn": 0.5,
            "family_members": [
                {"id": "fm_wife", "name": "默认妻", "relation": "wife", "age": 27, "location": "shengze", "alive": True, "notes": ""}
            ],
        }
    }
    result = extract_initial_state_from_character(None, identity_config)
    print(f"\n[测试3] identity_config.base_state 兜底（cc 为空）")
    print(f"  source = {result['source']}")
    assert result["cash"] == 7.5, f"got {result['cash']}"
    assert result["debt"] == 1.0
    assert result["rice"] == 2.0
    assert len(result["family_members"]) == 1
    assert result["source"] == "identity_base", f"source should be identity_base, got {result['source']}"
    print("  ✅ 全部通过")


def test_apply_initial_state():
    """场景：把解析结果应用到 GameState"""
    from history_footnote.initial_state_resolver import apply_initial_state, extract_initial_state_from_character
    from history_footnote.game_state import GameState, make_initial_state
    # 拿一个真实 era config
    import json
    era_config = json.loads((ROOT / "eras/wanli1587/era.json").read_text())
    state = make_initial_state("wanli1587", era_config, selected_identity="weaving_male")
    # 应用前
    assert state.cash == 0.0
    assert state.debt == 0.0
    assert state.family_members == []
    # 应用沈织户人设
    cc = {
        "name": "沈织户",
        "background": "沈家原也不是盛泽本地人...欠着绸缎牙行周二爷三两银子的旧账",
        "starting_situation": "手头现银一两二钱，欠牙行周二爷三两（利息每月三分）...马上要交春税折银（合四钱二分）",
        "family": {"mother": "张氏（58岁）", "wife": "张氏（26岁）", "son": "大毛（5岁）"},
    }
    identity_config = era_config["world"]["player_identities"]["weaving_male"]
    initial = extract_initial_state_from_character(cc, identity_config)
    apply_initial_state(state, initial)
    print(f"\n[测试4] apply_initial_state 写入 GameState")
    print(f"  state.cash = {state.cash}")
    print(f"  state.debt = {state.debt}")
    print(f"  state.monthly_burn = {state.monthly_burn}")
    print(f"  state.family_members count = {len(state.family_members)}")
    print(f"  state.active_tasks count = {len(state.active_tasks)}")
    assert state.cash == 1.2, f"cash should be 1.2, got {state.cash}"
    assert state.debt == 3.0, f"debt should be 3.0, got {state.debt}"
    assert abs(state.monthly_burn - 0.42) < 0.01, f"monthly_burn ~0.42, got {state.monthly_burn}"
    assert len(state.family_members) == 3, f"family count should be 3, got {len(state.family_members)}"
    assert state.financial_status.get("initial_state_source") in ("llm_text_parsed", "llm_struct", "identity_base"), \
        f"source should be set, got {state.financial_status.get('initial_state_source')}"
    print("  ✅ 全部通过")


def test_format_state_character_flatten():
    """场景：format_state 暴露 character 顶层字段（兼容前端 char-card）"""
    from history_footnote.web_server.views.format_state import _flatten_custom_character
    cc = {
        "name": "沈织户",
        "age": 30,
        "occupation": "丝织户",
        "background": "来历文字",
        "starting_situation": "处境文字",
        "family": {"wife": "张氏"},
        "voices": [{"name": "声音1"}],
    }
    flat = _flatten_custom_character(cc)
    print(f"\n[测试5] format_state 顶层 character 字段")
    print(f"  flat keys: {sorted(flat.keys())}")
    assert flat["name"] == "沈织户"
    assert flat["age"] == 30
    assert flat["background"] == "来历文字"
    assert flat["starting_situation"] == "处境文字"
    assert len(flat["voices"]) == 1
    print("  ✅ 全部通过")


def test_e2e_user_narrative():
    """端到端：用户提供的完整 narrative → 完整 state"""
    from history_footnote.initial_state_resolver import extract_initial_state_from_character, apply_initial_state
    from history_footnote.game_state import make_initial_state
    import json
    era_config = json.loads((ROOT / "eras/wanli1587/era.json").read_text())
    state = make_initial_state("wanli1587", era_config, selected_identity="weaving_male")
    # 用户实际 narrative
    cc = {
        "name": "沈织户",
        "age": 30,
        "occupation": "织工",
        "background": "沈家原也不是盛泽本地人，正德年间祖上从嘉兴府桐乡逃水患过来，在盛泽镇东巷子买了这两间屋子、置了一台旧织机，从此落脚。传到沈织户手里，织机是两台，欠着绸缎牙行周二爷三两银子的旧账，去年添丁没添进，反倒赔了一台机子的经钱。母亲张氏本是邻村张裁缝的闺女，嫁过来十六年，眼睛是生孩子时落下的病，见风就流泪，看不了细活。沈织户自己没什么大志向，就指望两个机子转得动、年底能把欠账还清、明年把大毛送去学点正经手艺。万历十五年开春，张居正的人早已倒台，矿税监没到盛泽，可里甲的折银、加派一点点压下来，丝价倒比去年贱了一成——他心里清楚，这一年不好过。",
        "starting_situation": "手头现银一两二钱，欠牙行周二爷三两（利息每月三分），上月赊的桑叶钱八钱还没结。马上要交春税折银（合四钱二分），大毛束脩下月也该续了。两台机子一台织湖绫、一台织包头绢，张氏帮着络丝，老娘绕纡子。前日里长来敲门说今年加派又要'议一议'。昨夜梦见周老爷来收账，醒来一身的冷汗。",
        "family": {
            "wife": "张氏（26岁）",
            "mother": "张氏（58岁）",
            "son": "大毛（5岁）",
        },
    }
    identity_config = era_config["world"]["player_identities"]["weaving_male"]
    initial = extract_initial_state_from_character(cc, identity_config)
    apply_initial_state(state, initial)
    print(f"\n[测试6] 端到端：用户 narrative → state")
    print(f"  source = {initial['source']}")
    print(f"  state.cash = {state.cash}  (期望 1.2)")
    print(f"  state.debt = {state.debt}  (期望 3.0)")
    print(f"  state.monthly_burn = {state.monthly_burn}  (期望 ~0.42)")
    print(f"  state.family_members = {[m['name'] for m in state.family_members]}")
    print(f"  state.active_tasks = {[t['title'][:30] for t in state.active_tasks]}")
    print(f"  state.upcoming_deadlines = {[d['name'] for d in state.upcoming_deadlines]}")
    # 关键断言：用户应该看到的右侧 sidebar 数据
    assert state.cash == 1.2, f"❌ cash 应为 1.2，实际 {state.cash}"
    assert state.debt == 3.0, f"❌ debt 应为 3.0，实际 {state.debt}"
    family_names = [m["name"] for m in state.family_members]
    assert any("张氏" in n for n in family_names), f"❌ 应有张氏，实际 {family_names}"
    assert "大毛" in family_names, f"❌ 应有大毛，实际 {family_names}"
    print("\n  ✅ 全部通过 — 右侧 sidebar 将不再显示 0")


def main():
    print("=" * 60)
    print("🆕 v1.9.5 initial_state_resolver 测试套件")
    print("=" * 60)
    test_chinese_number_parser()
    test_extract_from_text_only()
    test_llm_struct_priority()
    test_base_state_fallback()
    test_apply_initial_state()
    test_format_state_character_flatten()
    test_e2e_user_narrative()
    print("\n" + "=" * 60)
    print("✅ 所有测试通过（7 套）")
    print("=" * 60)


if __name__ == "__main__":
    main()
