"""🆕 v1.7.33 game_loop 集成 + 价格表读取 静态测试

覆盖：
1. game_loop 调 action_resolver（步骤 4.6）
2. set_action_context_for_dm 注入
3. _get_price 从 era_config 读
4. action_resolver 完整流程
5. 端到端：5 玩家输入 → 状态 + 事件
"""
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
GL = ROOT / "src/history_footnote/game_loop.py"
AR = ROOT / "src/history_footnote/action_resolver.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_game_loop_calls_action_resolver():
    print("[1/5] game_loop 步骤 4.6 调 action_resolver")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  parse_player_input + resolve_action + apply_action_result",
        "from history_footnote.action_resolver import" in src
        and "parse_player_input(player_input)" in src
        and "resolve_action(self.state, player_action" in src
        and "apply_action_result(self.state, action_result)" in src,
    )


def test_set_action_context_for_dm():
    print("\n[2/5] set_action_context_for_dm 注入")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  set_action_context_for_dm 定义 + 注入 state_ref",
        "def set_action_context_for_dm" in src
        and 'current_ref["action_context"]' in src
        and "events_triggered" in src
        and "narrative_hints" in src,
    )


def test_get_price_from_era_config():
    print("\n[3/5] _get_price 从 era_config 读")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.action_resolver import _get_price

    # mock config
    config = {
        "world": {
            "economy": {
                "price_anchor": {
                    "silk_bolt": "0.5-0.8",  # 范围
                    "rice_per_dan": 1.5,  # 具体值
                    "thread": 0.05,
                }
            }
        }
    }
    ok = True
    ok = _step("  silk_bolt 范围 0.5-0.8 → 0.65", abs(_get_price(config, "silk_bolt") - 0.65) < 0.01) and ok
    ok = _step("  rice_per_dan 具体 1.5", abs(_get_price(config, "rice_per_dan") - 1.5) < 0.01) and ok
    ok = _step("  thread 具体 0.05", abs(_get_price(config, "thread") - 0.05) < 0.01) and ok
    ok = _step("  缺省 0.5", abs(_get_price(config, "unknown") - 0.5) < 0.01) and ok
    # 无 config
    ok = _step("  无 config → 0.5", abs(_get_price(None, "x") - 0.5) < 0.01) and ok
    return ok


def test_full_action_resolver_with_config():
    print("\n[4/5] action_resolver 完整流程（用 config）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.action_resolver import parse_player_input, resolve_action, apply_action_result

    s = GameState()
    s.cash = 5.0

    config = {"world": {"economy": {"price_anchor": {"silk_bolt": "0.5-0.8"}}}}
    a = parse_player_input("我卖了湖绫")
    r = resolve_action(s, a, config)
    apply_action_result(s, r)
    all_ok = _step(f"  silk_bolt 范围 → cash={s.cash:.2f}（期望 5.65）", abs(s.cash - 5.65) < 0.01)
    return all_ok


def test_e2e_five_inputs():
    print("\n[5/5] 端到端：5 玩家输入 → 状态 + 事件")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.action_resolver import parse_player_input, resolve_action, apply_action_result

    s = GameState()
    s.cash = 5.0
    s.debt = 0.0
    s.current_city = "shengze"

    inputs = [
        ("我织了一匹湖绫", "CRAFT", "discover.item"),
        ("我卖了湖绫", "SELL", "fin.sell_silk"),
        ("我搭船去苏州", "TRAVEL", "city.arrive.suzhou"),
        ("我见沈氏", "MEET", "discover.person"),
        ("我借五两", "BORROW", "fin.borrow"),
    ]
    ok = True
    for text, expected_verb, expected_event in inputs:
        a = parse_player_input(text)
        if a.verb != expected_verb:
            ok = _step(f"  '{text}' verb={expected_verb}", False) and ok
            continue
        r = resolve_action(s, a)
        apply_action_result(s, r)
        event_ids = [e.get("id", "") for e in r.events]
        match = expected_event in event_ids
        ok = _step(f"  '{text}' → {expected_event}", match) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.33 game_loop 集成 + 价格表 静态测试 ===\n")
    ok1 = test_game_loop_calls_action_resolver()
    ok2 = test_set_action_context_for_dm()
    ok3 = test_get_price_from_era_config()
    ok4 = test_full_action_resolver_with_config()
    ok5 = test_e2e_five_inputs()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
