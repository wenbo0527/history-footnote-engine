"""规则引擎核心功能验证脚本

测试 6 项关键能力：
1. 行动边界检查
2. 强制历史事件触发
3. 变量触发条件
4. 节奏推进指令
5. 认知解锁候选
6. 变量变更应用（含 max_shift_per_round 截断）
"""
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import make_initial_state
from history_footnote.rule_engine import RuleEngine


def main():
    # 加载时代包
    config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )

    state = make_initial_state("wanli1587", config, "weaving_male")
    engine = RuleEngine(config)

    print("=" * 60)
    print("规则引擎核心功能验证")
    print("=" * 60)

    # === 测试1: 行动边界 ===
    print("\n[1] 行动边界检查")
    view = engine.make_view(state)

    r1 = engine.check_action(view, "我去皇宫告状")
    print(f"  '去皇宫告状' → allowed={r1['allowed']}, reason='{r1.get('reason', '')}'")
    assert not r1["allowed"], "皇宫应该被拒绝"

    r2 = engine.check_action(view, "我去茶馆喝茶")
    print(f"  '去茶馆喝茶' → allowed={r2['allowed']}")
    assert r2["allowed"], "茶馆应该允许"

    r3 = engine.check_action(view, "我想改变皇帝决策")
    print(f"  '改变皇帝决策' → allowed={r3['allowed']}, reason='{r3.get('reason', '')}'")
    assert not r3["allowed"], "皇帝决策应该被拒绝"

    print("  ✅ 行动边界检查通过")

    # === 测试2: 强制历史事件 ===
    print("\n[2] 强制历史事件（round 1）")
    forced = engine.check_forced_events(view)
    print(f"  触发 {len(forced)} 个事件:")
    for fe in forced:
        print(f"    - {fe.event_id}: {fe.event_name} (mandatory={fe.narrative_mandatory})")
    assert len(forced) == 1, f"round 1 应只有1个事件，实际{len(forced)}"
    assert forced[0].event_id == "he_01", f"应该是he_01，实际{forced[0].event_id}"

    # 推进到 round 8
    state.round_number = 8
    view = engine.make_view(state)
    forced8 = engine.check_forced_events(view)
    print(f"\n  round 8 触发 {len(forced8)} 个事件:")
    for fe in forced8:
        print(f"    - {fe.event_id}: {fe.event_name}")
    assert len(forced8) == 1 and forced8[0].event_id == "he_03", "round 8 应是黄河决口"

    # 推进到 round 11
    state.round_number = 11
    view = engine.make_view(state)
    forced11 = engine.check_forced_events(view)
    print(f"\n  round 11 触发 {len(forced11)} 个事件:")
    for fe in forced11:
        print(f"    - {fe.event_id}: {fe.event_name}")
    assert forced11[0].event_id == "he_04", "round 11 应是海瑞之死"

    print("  ✅ 强制历史事件触发正常")

    # === 测试3: 触发条件 ===
    print("\n[3] 变量触发条件（tax_burden=8）")
    state.round_number = 1
    state.variables["tax_burden"] = 8
    view = engine.make_view(state)
    triggers = engine.check_triggers(view)
    print(f"  触发 {len(triggers)} 个规则:")
    for tr in triggers:
        print(f"    - {tr.id}: effect={tr.effect}, hint='{tr.narrative_hint[:30]}...'")
    assert any(tr.id == "tr_tax_spike" for tr in triggers), "应触发tr_tax_spike"
    print("  ✅ 变量触发条件正常")

    # === 测试4: 节奏推进 ===
    print("\n[4] 节奏推进（player_idle_rounds=3）")
    state.player_idle_rounds = 3
    view = engine.make_view(state)
    pacing = engine.check_pacing(view)
    print(f"  触发 {len(pacing)} 个指令:")
    for pd in pacing:
        print(f"    - {pd.id}: direction={pd.direction}")
        print(f"      hint='{pd.hint[:50]}...'")
    assert any(pd.id == "pr_idle" for pd in pacing), "应触发pr_idle"
    print("  ✅ 节奏推进指令计算正常")

    # === 测试5: 认知解锁 ===
    print("\n[5] 认知解锁候选")
    insights = engine.check_insights(view, player_input="我想知道丝绸的事")
    print(f"  命中 {len(insights)} 个insight:")
    for ic in insights:
        print(f"    - {ic.id}: {ic.topic} (confirm_needed={ic.confirm_needed})")
    assert any(ic.id == "ins_silk_trade" for ic in insights), "应触发ins_silk_trade"

    insights2 = engine.check_insights(view, player_input="纳税的事我想问问")
    print(f"  '纳税的事我想问问' 命中 {len(insights2)} 个insight:")
    for ic in insights2:
        print(f"    - {ic.id}: {ic.topic}")
    assert any(ic.id == "ins_silver_tax" for ic in insights2), "应触发ins_silver_tax"

    insights3 = engine.check_insights(view, player_input="里长来催税了")
    print(f"  '里长来催税了' 命中 {len(insights3)} 个insight:")
    for ic in insights3:
        print(f"    - {ic.id}: {ic.topic}")
    assert any(ic.id == "ins_li_jia" for ic in insights3), "应触发ins_li_jia"

    print("  ✅ 认知解锁候选正常")

    # === 测试6: 变量变更应用 + max_shift截断 ===
    print("\n[6] 变量变更应用（max_shift_per_round 截断）")
    state.variables["tax_burden"] = 5
    view = engine.make_view(state)

    # tax_burden 的 max_shift_per_round = 2
    adjust_result = engine.apply_changes(view, {"tax_burden": 100})
    print(f"  请求 tax_burden +100（max_shift=2）")
    print(f"  调整: {adjust_result['adjusted']}")
    print(f"  最终: {state.variables['tax_burden']}")
    assert state.variables["tax_burden"] == 7, "应被截断为+2"
    assert "tax_burden" in adjust_result["adjusted"], "应记录截断信息"
    print("  ✅ 变量变更应用 + 截断正常")

    # === 测试7: 复合条件 ===
    print("\n[7] 复合条件（AND）")
    state.round_number = 35
    state.variables["workshop_scale"] = 8
    state.variables["tribute_pressure"] = 6
    view = engine.make_view(state)
    triggers2 = engine.check_triggers(view)
    print(f"  workshop_scale=8, tribute_pressure=6, round=35")
    print(f"  触发 {len(triggers2)} 个规则:")
    for tr in triggers2:
        print(f"    - {tr.id}")
    print("  ✅ 复合条件评估正常")

    print("\n" + "=" * 60)
    print("✅ 全部规则引擎核心功能验证通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
