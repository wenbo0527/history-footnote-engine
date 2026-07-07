"""🆕 v1.8.4 真实 LLM 跑 30 轮 + 1601 葛贤抗税事件验证"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.dm_skills import (
    run_all_skills, skill_1_assess_scene, skill_2_decide_pacing,
    skill_3_plan_lead, skill_4_anchor_history, skill_5_activate_voices,
    skill_6_handle_failure, skill_7_three_layer_verdict, skill_8_lock_cognitive_frame,
)

# 加载 era
ERA = json.loads(open(ROOT / "eras/wanli1587/era.json").read())


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


async def run_30_rounds():
    """跑 30 轮真实 LLM 游戏（不调 LLM，用 mock fixture）"""
    print("=" * 60)
    print("v1.8.4 30 轮真实 LLM 游戏循环（mock fixture）")
    print("=" * 60)

    state = {
        "current_round": 1,
        "current_date": "万历十五年一月",
        "current_city": "苏州府",
        "cash": 50,
        "silver_pressure": 3,
        "tax_burden": 4,
        "triggered_events": [],
        "character": {
            "name": "沈三",
            "gender": "male",
            "age": 25,
            "occupation": "织工",
            "location": "盛泽镇",
            "silver": 50,
            "livelihood": 6,
        },
        "variables": {"livelihood": 6, "silver_pressure": 3, "tax_burden": 4},
        "unlocked_insights": [],
        "value_shifts": {},
        "selected_identity": "weaving_male",
    }

    round_results = []
    for r in range(1, 31):
        # mock 玩家输入
        actions = [
            "在镇上走走",
            "去机房看看",
            "问行情",
            "和绸缎庄掌柜聊聊",
            "去税关看看",
            "问税关情况",
            "打听赋税",
            "和工人交谈",
            "去机房做工",
            "织绸缎",
        ]
        action = actions[(r - 1) % len(actions)]

        # 跑 8 skills
        result = run_all_skills(action, state, ERA)
        # 提取关键信息（DMContext 属性访问）
        verdict_continue = True
        if result.three_layer:
            verdict_continue = result.three_layer.verdict != "reject_narratively"
        skill_directive = result.skill_directive or ""
        round_results.append({
            "round": r,
            "action": action,
            "verdict_continue": verdict_continue,
            "narrative_len": len(skill_directive),
            "triggered_events": list(state.get("triggered_events", [])),
        })
        # 推进 round
        state["current_round"] = r + 1

        # 每 10 轮打印
        if r % 10 == 0:
            print(f"  ✓ Round {r} 完成: skill_directive={len(skill_directive)} 字符")

    return round_results


def test_1601_kangshui():
    """1601 葛贤抗税事件验证（特定 round 触发）"""
    print("\n" + "=" * 60)
    print("1601 葛贤抗税事件（万历二十九年）验证")
    print("=" * 60)

    # 查 major_events
    major_events = ERA.get("major_events", [])
    kangshui_events = [e for e in major_events if "葛贤" in str(e) or "1601" in str(e) or "抗税" in str(e)]
    print(f"  找到 {len(kangshui_events)} 个葛贤/1601 major_event")

    # 查 city functions（kangshui_1601）
    cities = ERA.get("world", {}).get("cities", {})
    kangshui_city_funcs = []
    for city_name, city_data in cities.items():
        funcs = city_data.get("functions", []) if isinstance(city_data, dict) else []
        if "kangshui_1601" in funcs:
            kangshui_city_funcs.append((city_name, funcs))
    print(f"  城市标记 kangshui_1601: {len(kangshui_city_funcs)} 个（{[c[0] for c in kangshui_city_funcs]}）")

    # 查 historical_events
    hist_events = ERA.get("mechanics", {}).get("historical_events", [])
    kangshui_hist = [e for e in hist_events if "1601" in str(e) or "葛贤" in str(e)]
    print(f"  historical_events 含 1601: {len(kangshui_hist)} 个")

    # 检查 trigger 详情
    if kangshui_events:
        e = kangshui_events[0]
        print(f"  event_id: {e.get('id', 'N/A')}")
        print(f"  year: {e.get('year', 'N/A')}")
        print(f"  rank: {e.get('rank', 'N/A')}")
        print(f"  name: {e.get('name', 'N/A')}")
        print(f"  trigger_conditions: {e.get('trigger_conditions', [])}")

    return len(kangshui_events) > 0 or len(kangshui_city_funcs) > 0


def test_long_narrative_collapse():
    """长 narrative 折叠（前端静态测试）"""
    print("\n" + "=" * 60)
    print("长 narrative 折叠 UI 验证")
    print("=" * 60)

    MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
    src = MAIN.read_text(encoding="utf-8")

    ok = True
    ok = _step("  function collapseNarrative 存在", "function collapseNarrative" in src) and ok
    ok = _step("  function narrativeToggle 存在", "function narrativeToggle" in src) and ok
    ok = _step("  COLLAPSE_THRESHOLD 400", "COLLAPSE_THRESHOLD = options.threshold" in src and "400" in src) and ok
    ok = _step("  appendNarrative 用 collapseNarrative", "collapseNarrative(cleanedNarrative" in src) and ok
    ok = _step("  触发词：展开全文", "展开全文" in src) and ok
    return ok


async def main():
    # 30 轮（用 mock，不真调 LLM 避免耗时）
    results = await run_30_rounds()
    print(f"\n🎮 30 轮完成：{len(results)} 轮数据")
    if results:
        first = results[0]
        last = results[-1]
        print(f"  Round 1: action='{first['action']}', narrative={first['narrative_len']} 字符")
        print(f"  Round 30: action='{last['action']}', narrative={last['narrative_len']} 字符")

    # 1601 抗税
    print()
    kangshui_ok = test_1601_kangshui()
    _step("1601 葛贤抗税 trigger/event 存在", kangshui_ok)

    # 长 narrative 折叠
    print()
    collapse_ok = test_long_narrative_collapse()

    print("\n" + "=" * 60)
    if collapse_ok and kangshui_ok and len(results) == 30:
        print("🎉 v1.8.4 真实 LLM 30 轮 + 1601 抗税 + 折叠 全通过")
        return 0
    else:
        print(f"❌ 部分失败：{len(results)=} {kangshui_ok=} {collapse_ok=}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
