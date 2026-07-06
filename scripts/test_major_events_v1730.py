"""🆕 v1.7.30 重大历史事件 静态测试

覆盖：
1. era.json era.major_events 10 大事件
2. era.json era.timeline_overview 16 年时间线
3. era.json era.event_id_namespaces evt.* 4 类
4. event_parser evt.* 处理器 + 12 条 EVT_ROUTING
5. system_prompt 加 evt.* 段
6. evt.* → fin.* 路由（5 条）
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
ERA = ROOT / "eras/wanli1587/era.json"
EP = ROOT / "src/history_footnote/event_parser.py"
SP = ROOT / "src/history_footnote/dm/prompts/system_base.md"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_10_major_events():
    print("[1/6] era.json 11 大事件（矿税+葛贤抗税+三大征+水灾+辽东+5个P2背景）")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    events = era.get("era", {}).get("major_events", [])
    p0 = [e for e in events if e.get("rank") == "P0"]
    p1 = [e for e in events if e.get("rank") == "P1"]
    p2 = [e for e in events if e.get("rank") == "P2"]
    ok = True
    ok = _step(f"  11 大事件（实际 {len(events)}）", len(events) >= 10) and ok
    ok = _step(f"  P0: 矿税/葛贤抗税（实际 {len(p0)}）", len(p0) == 2) and ok
    ok = _step(f"  P1: 三大征/水灾/辽东（实际 {len(p1)}）", len(p1) == 3) and ok
    ok = _step(f"  P2: ≥5（实际 {len(p2)}）", len(p2) >= 5) and ok
    return ok


def test_timeline():
    print("\n[2/6] era.json 时间线 16 年")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    tl = era.get("era", {}).get("timeline_overview", [])
    return _step(
        f"  16 年时间线（实际 {len(tl)}）",
        len(tl) == 16,
    )


def test_evt_namespaces():
    print("\n[3/6] era.json evt.* 4 类")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    ns = era.get("era", {}).get("event_id_namespaces", {}).get("evt.*", {})
    domains = ns.get("domains", {})
    expected = ["evt.tax.*", "evt.flood.*", "evt.war.*", "evt.chaos.*"]
    ok = True
    for d in expected:
        ok = _step(f"  {d} 在 domains", d in domains) and ok
    return ok


def test_event_parser_evt_routing():
    print("\n[4/6] event_parser evt.* 12 条路由")
    src = EP.read_text(encoding="utf-8")
    expected_evt_ids = [
        "evt.tax.weaving_machine", "evt.tax.silk_per_pi", "evt.tax.checkpoint", "evt.tax.liao_taxes",
        "evt.flood.mulberry_loss", "evt.flood.rice_price_spike", "evt.flood.silk_price_down",
        "evt.war.silver_outflow", "evt.war.transit_disrupted", "evt.war.army_demand",
        "evt.chaos.worker_revolt", "evt.chaos.armed_conflict",
    ]
    ok = True
    ok = _step("  EVT_ROUTING 字典定义", "EVT_ROUTING = {" in src) and ok
    ok = _step("  _apply_evt_event 函数", "def _apply_evt_event" in src) and ok
    ok = _step('  _HANDLERS["evt"] = _apply_evt_event', '_HANDLERS["evt"]' in src) and ok
    for eid in expected_evt_ids:
        ok = _step(f"  {eid} 在 EVT_ROUTING", f'"{eid}"' in src) and ok
    return ok


def test_system_prompt_evt():
    print("\n[5/6] system_prompt evt.* 段")
    src = SP.read_text(encoding="utf-8")
    ok = True
    ok = _step("  15 类 EventId 提示（14 原 + evt.*）", "15 类事件 id 前缀" in src) and ok
    ok = _step("  evt.* 4 类子域", "evt.tax.*" in src and "evt.flood.*" in src and "evt.war.*" in src and "evt.chaos.*" in src) and ok
    ok = _step("  葛贤抗税提示（关键 P0）", "葛贤抗税" in src) and ok
    ok = _step("  三大征→矿税→孙隆→水灾→葛贤（核心传导链）", "三大征" in src and "矿税" in src and "孙隆" in src) and ok
    ok = _step("  evt.* vs fin.* 区别", "evt.* vs fin.*" in src) and ok
    return ok


def test_evt_routing_end_to_end():
    """端到端：5 条 evt.* 路由到 fin.*"""
    print("\n[6/6] 端到端：evt.* 路由到 fin.* 写入 financial_log")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.event_parser import parse_events, apply_event

    s = GameState()
    s.round_number = 5
    s.current_date = "1587年3月"
    s.cash = 5.0

    llm = """<events>
  <event id="evt.tax.weaving_machine" amount="0.3" note="万历二十七年孙隆加征"/>
  <event id="evt.flood.mulberry_loss" amount="0.5" note="万历十五年江南大水"/>
  <event id="evt.war.silver_outflow" amount="0.2" note="万历朝鲜之役军费"/>
  <event id="evt.chaos.worker_revolt" amount="0.1" note="万历二十九年葛贤抗税"/>
  <event id="evt.flood.silk_price_down" amount="-0.5" note="水灾导致丝价跌"/>
</events>"""
    events = parse_events(llm)
    applied = 0
    for ev in events:
        if apply_event(s, ev):
            applied += 1
    return _step(
        f"  5/5 evt.* 路由到 fin.* 成功（实际 {applied}/{len(events)}）",
        applied == 5,
    )


if __name__ == "__main__":
    print("=== v1.7.30 重大历史事件 静态测试 ===\n")
    ok1 = test_10_major_events()
    ok2 = test_timeline()
    ok3 = test_evt_namespaces()
    ok4 = test_event_parser_evt_routing()
    ok5 = test_system_prompt_evt()
    ok6 = test_evt_routing_end_to_end()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
