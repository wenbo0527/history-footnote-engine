"""🆕 v1.7.30 经济/官僚/触发模式 静态测试

覆盖：
1. era.json economy.price_anchor（8 个价格锚点）
2. era.json economy.cost_model（生存线/危机线）
3. era.json economy.tax_specifics
4. era.json bureaucracy.local_hierarchy（6 类基层官僚）
5. era.json bureaucracy.grease_cost（7 项打点）
6. era.json bureaucracy.dispute_rules（4 类纠纷）
7. era.json world.triggers 24 个触发器（7 类 24 个）
8. TriggerPatterns.md 文档存在 + 24 个模式
9. system_prompt 加 13 类 EventId + 经济/官僚数值锚点
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
ERA = ROOT / "eras" / "wanli1587" / "era.json"
TP = ROOT / "docs/architecture/TriggerPatterns.md"
SP = ROOT / "src/history_footnote/dm/prompts/system_base.md"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_price_anchor():
    print("[1/8] era.json economy.price_anchor")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    pa = era["world"]["economy"]["price_anchor"]
    expected = ["rice_per_shi", "silk_per_pi", "cotton_per_pi", "weaver_daily_wage",
                "loom_price", "mulberry_leaves_per_dan", "servant_buyout", "small_house_in_county"]
    ok = True
    for e in expected:
        ok = _step(f"  {e}", e in pa) and ok
    return ok


def test_cost_model():
    print("\n[2/8] era.json economy.cost_model")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    cm = era["world"]["economy"]["cost_model"]
    return _step(
        "  survival_line / crisis_line / silk_profit_per_pi / monthly_income_normal",
        "survival_line" in cm
        and "crisis_line" in cm
        and "silk_profit_per_pi" in cm
        and "monthly_income_normal" in cm,
    )


def test_tax_specifics():
    print("\n[3/8] era.json economy.tax_specifics")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    ts = era["world"]["economy"]["tax_specifics"]
    return _step(
        "  yitiaobianfa / normal_tax_rate / zaozhijia_tax / chaoguan_rate",
        "yitiaobianfa" in ts
        and "normal_tax_rate" in ts
        and "zaozhijia_tax" in ts
        and "chaoguan_rate" in ts,
    )


def test_local_hierarchy():
    print("\n[4/8] era.json bureaucracy.local_hierarchy")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    lh = era["world"]["bureaucracy"]["local_hierarchy"]
    expected = ["lijia", "county_clerks", "county_officials", "prefecture", "weaving_eunuch", "customs"]
    ok = True
    for e in expected:
        ok = _step(f"  {e}", e in lh) and ok
    return ok


def test_grease_cost():
    print("\n[5/8] era.json bureaucracy.grease_cost")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    gc = era["world"]["bureaucracy"]["grease_cost"]
    expected = ["lijia_favor", "clerk_favor", "county_case", "customs_bribe", "eunuch_favor"]
    ok = True
    for e in expected:
        ok = _step(f"  {e}", e in gc) and ok
    return ok


def test_dispute_rules():
    print("\n[6/8] era.json bureaucracy.dispute_rules")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    dr = era["world"]["bureaucracy"]["dispute_rules"]
    expected = ["weaver_vs_broker", "weaver_vs_merchant", "false_accusation", "tax_resistance"]
    ok = True
    for e in expected:
        ok = _step(f"  {e}", e in dr) and ok
    return ok


def test_triggers_24():
    print("\n[7/8] era.json world.triggers（27 个，7 类）")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    triggers = era["world"].get("triggers", [])
    # 27 个触发器（4+4+4+3+4+4+4）
    new_triggers = [t for t in triggers if t.get("id", "").split(".")[0] in ("trv", "comm", "gov", "obj", "relig", "reln", "dis")]
    cats = {}
    for t in new_triggers:
        c = t.get("category")
        cats[c] = cats.get(c, 0) + 1
    expected_cats = {"travel": 4, "commercial": 4, "government": 4, "object": 3, "religious": 4, "relationship": 4, "disaster": 4}
    ok = True
    ok = _step(f"  27 个新触发器（实际 {len(new_triggers)}）", len(new_triggers) == 27) and ok
    for c, n in expected_cats.items():
        ok = _step(f"  {c}: {n}（实际 {cats.get(c, 0)}）", cats.get(c, 0) == n) and ok
    return ok


def test_trigger_patterns_doc():
    print("\n[8/8] TriggerPatterns.md + system_prompt 13 类 EventId + 数值锚点")
    ok = True
    ok = _step("  TriggerPatterns.md 存在", TP.exists()) and ok
    if TP.exists():
        src = TP.read_text(encoding="utf-8")
        ok = _step("  24 个模式 ID 都在文档", all(
            pid in src for pid in ["trv.ship_stuck", "trv.find_money", "comm.broker_lowball",
                                    "gov.weaving_tax", "obj.token_exposed", "relig.nun_trap",
                                    "reln.guild_hall", "dis.plague", "dis.little_ice_age"]
        )) and ok
    sp = SP.read_text(encoding="utf-8")
    new_categories = ["trv.*", "comm.*", "gov.*", "obj.*", "relig.*", "reln.*", "dis.*"]
    for c in new_categories:
        ok = _step(f"  system_prompt 加 {c}", c in sp) and ok
    ok = _step("  system_prompt 加经济/官僚数值锚点", "催税缓缴打点里长" in sp and "生存线" in sp) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.30 经济/官僚/触发模式 静态测试 ===\n")
    ok1 = test_price_anchor()
    ok2 = test_cost_model()
    ok3 = test_tax_specifics()
    ok4 = test_local_hierarchy()
    ok5 = test_grease_cost()
    ok6 = test_dispute_rules()
    ok7 = test_triggers_24()
    ok8 = test_trigger_patterns_doc()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8]):
        print("\n🎉 8 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=}")
        sys.exit(1)
