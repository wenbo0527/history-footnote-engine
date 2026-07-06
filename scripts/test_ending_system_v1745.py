"""🆕 v1.7.45 EndingSystem 静态测试"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
ES = ROOT / "src/history_footnote/ending_system.py"
GEF = ROOT / "src/history_footnote/game_engine_facade.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_8_endings_defined():
    print("[1/6] 8 结局定义")
    src = ES.read_text(encoding="utf-8")
    endings = [
        ("MERCHANT_EMPIRE", "盛世商贾", 100),
        ("LOYAL_RESIST", "忠义抗税", 90),
        ("OVERSEAS_PIONEER", "出海冒险", 80),
        ("SCHOLAR_SUCCESS", "学而优", 80),
        ("PEACEFUL_FAMILY", "田园归隐", 60),
        ("COMFORTABLE", "小康安稳", 50),
        ("STRUGGLING", "勉强维持", 30),
        ("BANKRUPT_BEGGAR", "破产流民", 20),
    ]
    ok = True
    for var, name, priority in endings:
        has_var = f"ENDING_{var.split('_')[0]}" in src or f"ENDING_{var}" in src
        has_name = name in src
        has_priority = str(priority) in src
        ok = _step(f"  {name} (priority={priority})", has_var and has_name and has_priority) and ok
    return ok


def test_priority_order():
    print("\n[2/6] 优先级排序")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.ending_system import EndingSystem
    from history_footnote.game_state import GameState

    s = GameState()
    s.cash = 60.0
    s.debt = 0.0
    s.round_number = 50
    s.triggered_events = ["evt.guoben_dispute"]
    es = EndingSystem()
    ending = es.check(s)
    all_ok = _step(f"  cash=60 + evt.guoben_dispute → 盛世商贾 (priority=100 优先于 90)",
                   ending and ending.type == "merchant_empire")
    return all_ok


def test_check_8_conditions():
    print("\n[3/6] 8 条件全检查")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.ending_system import EndingSystem
    from history_footnote.game_state import GameState

    es = EndingSystem()
    cases = [
        # (state_attrs, expected_type, label)
        ({"cash": 60, "debt": 0, "round": 50}, "merchant_empire", "cash=60 debt=0 round=50"),
        ({"cash": 10, "debt": 0, "events": ["evt.guoben_dispute"], "round": 30}, "loyal_resist", "evt.guoben_dispute"),
        ({"cash": 5, "city": "yuegang", "round": 30}, "overseas_pioneer", "city=yuegang"),
        ({"cash": -5, "round": 30}, "bankrupt_beggar", "cash=-5"),
        ({"cash": 10, "debt": 1, "tasks": ["quest.family_meet"], "round": 30}, "peaceful_family", "task.family_meet"),
        ({"cash": 20, "debt": 3, "round": 25}, "comfortable", "cash=20 round=25"),
        ({"cash": 0, "debt": 5, "round": 15}, "struggling", "cash=0 debt=5"),
    ]
    ok = True
    for attrs, expected, label in cases:
        s = GameState()
        s.cash = attrs.get("cash", 0)
        s.debt = attrs.get("debt", 0)
        s.round_number = attrs.get("round", 1)
        s.current_city = attrs.get("city", "shengze")
        s.triggered_events = attrs.get("events", [])
        # 处理 quest_states
        if "tasks" in attrs:
            s.quest_states = {tid: {"status": "completed"} for tid in attrs["tasks"]}
        ending = es.check(s)
        actual = ending.type if ending else None
        ok = _step(f"  {label} → {actual} (期望 {expected})", actual == expected) and ok
    return ok


def test_facade_check_ending():
    print("\n[4/6] facade.check_ending")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 60.0
    s.debt = 0.0
    s.round_number = 50
    facade = GameEngineFacade(s, era_config={})
    result = facade.check_ending()
    ok = _step(f"  check_ending 返回 {result.get('name') if result else None}",
               result and result.get("name") == "盛世商贾")
    ok = _step(f"  含 narrative 字段（{len(result.get('narrative', ''))} 字符）",
               result and len(result.get("narrative", "")) > 50) and ok
    ok = _step(f"  含 icon 🏆", result and result.get("icon") == "🏆") and ok
    return ok


def test_priority_dedup():
    print("\n[5/6] 同优先级去重")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.ending_system import EndingSystem
    from history_footnote.game_state import GameState

    # cash=80 + evt.guoben_dispute + city=yuegang
    # 应触发 merchant_empire (100) > loyal_resist (90) = overseas_pioneer (80)
    s = GameState()
    s.cash = 80.0
    s.debt = 0.0
    s.round_number = 50
    s.current_city = "yuegang"
    s.triggered_events = ["evt.guoben_dispute"]
    es = EndingSystem()
    ending = es.check(s)
    ok = _step(f"  高 cash + evt.guoben + yuegang → {ending.name} (期望盛世商贾)",
               ending and ending.type == "merchant_empire")
    return ok


def test_e2e_full_workflow():
    print("\n[6/6] 端到端：state 完整流程")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.ending_system import EndingSystem
    from history_footnote.game_state import GameState

    all_ok = True
    # 模拟玩家从破产到出海
    s = GameState()
    s.cash = -5.0
    s.debt = 0.0
    s.round_number = 30

    es = EndingSystem()
    ending1 = es.check(s)
    all_ok = _step(f"  初始 cash=-5 → 破产流民",
                   ending1 and ending1.type == "bankrupt_beggar") and all_ok

    # 改 cash
    s.cash = 5.0
    s.current_city = "yuegang"
    ending2 = es.check(s)
    all_ok = _step(f"  改 cash=5, city=yuegang → 出海冒险",
                   ending2 and ending2.type == "overseas_pioneer") and all_ok

    # 改 cash=80
    s.cash = 80.0
    ending3 = es.check(s)
    all_ok = _step(f"  改 cash=80 → 盛世商贾 (priority 100)",
                   ending3 and ending3.type == "merchant_empire") and all_ok

    # get_ending_summary
    summary = es.get_ending_summary()
    all_ok = _step(f"  8 结局都在 summary（{len(summary)} 个）", len(summary) == 8) and all_ok

    return all_ok


if __name__ == "__main__":
    print("=== v1.7.45 EndingSystem 静态测试 ===\n")
    ok1 = test_8_endings_defined()
    ok2 = test_priority_order()
    ok3 = test_check_8_conditions()
    ok4 = test_facade_check_ending()
    ok5 = test_priority_dedup()
    ok6 = test_e2e_full_workflow()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
