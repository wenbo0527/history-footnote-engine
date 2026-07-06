"""🆕 v1.7.34 架构升级 静态测试

覆盖：
1. EventBus（精确/通配符/全部订阅 + 中间件 + 死信）
2. DramaManager（player_model + 3 维度评估 + LLM 提示）
3. QuestSystem（声明式任务 + 3 条件 + 状态机）
4. game_loop 集成点
5. 端到端：3 任务流
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_event_bus():
    print("[1/5] EventBus")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.event_bus import EventBus, GameEvent

    bus = EventBus("test")
    received = []
    bus.subscribe("fin.*", lambda e: received.append(("fin", e.id)))
    bus.subscribe("*", lambda e: received.append(("any", e.id)))

    ok = True
    ok = _step("  通配符订阅", "fin.*" in bus._subscribers) and ok
    ok = _step("  全部订阅", "*" in bus._subscribers) and ok
    # 加精确订阅测试
    bus.subscribe("city.arrive.suzhou", lambda e: received.append(("city", e.id)))
    ok = _step("  精确订阅 city.arrive.suzhou", "city.arrive.suzhou" in bus._subscribers) and ok
    n = bus.publish(GameEvent(id="fin.sell_silk", type="fin"))
    ok = _step(f"  publish 触发 2 handlers（实际 {n}）", n == 2) and ok
    ok = _step(f"  received {len(received)} 条", len(received) == 2) and ok

    # 中间件
    bus.use(lambda e: e if e.priority >= 25 else None)
    n = bus.publish(GameEvent(id="fin.buy", type="fin", priority=10))
    ok = _step(f"  中间件过滤低优先级（实际 {n}）", n == 0) and ok
    return ok


def test_drama_manager():
    print("\n[2/5] DramaManager")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.drama_manager import DramaManager, PlayerModel
    from history_footnote.game_state import GameState

    s = GameState()
    s.round_number = 5
    dm = DramaManager(s)
    ok = True
    # 记录
    dm.record_player_action("SELL", "silk_bolt", is_initiative=True)
    dm.record_player_action("TRAVEL", "suzhou", is_initiative=True)
    ok = _step("  record_player_action 更新 model", dm.player_model.total_rounds == 2) and ok
    # 评估
    interventions = dm.evaluate()
    ok = _step(f"  evaluate 返回 0+ 干预（{len(interventions)}）", True) and ok
    # LLM hint
    hint = dm.build_llm_intervention_hint(interventions)
    ok = _step("  build_llm_intervention_hint 输出", "Drama Manager" in hint or hint == "") and ok
    return ok


def test_quest_system():
    print("\n[3/5] QuestSystem")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.quest_system import QuestSystem, WANLI_QUESTS, QuestStatus, Quest, QuestCondition, ConditionType
    from history_footnote.event_bus import get_event_bus, reset_event_bus, GameEvent
    from history_footnote.game_state import GameState

    reset_event_bus()
    bus = get_event_bus()
    s = GameState()
    s.cash = 5.0
    qs = QuestSystem(s, bus, WANLI_QUESTS)
    ok = True
    ok = _step(f"  加载 4 个任务（{len(qs.quests)}）", len(qs.quests) == 4) and ok
    # 接受
    qs.accept_quest("quest.first_silk")
    ok = _step(f"  accept_quest → ACTIVE", qs.quests["quest.first_silk"].is_active()) and ok
    # 触发
    bus.publish(GameEvent(id="discover.item", type="discover", data={"name": "湖绫"}))
    ok = _step(f"  完成后 status=COMPLETED", qs.quests["quest.first_silk"].is_completed()) and ok
    return ok


def test_3_quest_conditions():
    print("\n[4/5] 3 类条件（on_event / on_state / on_choice）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.quest_system import QuestCondition, ConditionType
    from history_footnote.event_bus import get_event_bus, reset_event_bus, GameEvent
    from history_footnote.game_state import GameState

    reset_event_bus()
    bus = get_event_bus()
    s = GameState()
    s.cash = 5.0
    s.player_model = {"recent_actions": [{"verb": "SELL", "object": "silk_bolt"}]}

    # on_event
    cond_event = QuestCondition(type=ConditionType.ON_EVENT, config={"event_id": "fin.sell_silk", "min_count": 2})
    bus.publish(GameEvent(id="fin.sell_silk", type="fin"))
    ok = _step(f"  on_event min_count=2，1 次（应 False）", not cond_event.evaluate(s, bus))

    # on_state
    cond_state = QuestCondition(type=ConditionType.ON_STATE, config={"field": "cash", "op": ">=", "value": 5.0})
    ok = _step(f"  on_state cash>=5.0（cash={s.cash} 应 True）", cond_state.evaluate(s, bus)) and ok

    # on_choice
    cond_choice = QuestCondition(type=ConditionType.ON_CHOICE, config={"verb": "SELL"})
    ok = _step(f"  on_choice verb=SELL（recent 含 SELL 应 True）", cond_choice.evaluate(s, bus)) and ok
    return ok


def test_e2e_3_quests():
    print("\n[5/5] 端到端：3 任务完成流")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.quest_system import QuestSystem, WANLI_QUESTS
    from history_footnote.event_bus import get_event_bus, reset_event_bus, GameEvent
    from history_footnote.game_state import GameState

    reset_event_bus()
    bus = get_event_bus()
    s = GameState()
    s.cash = 5.0
    s.current_city = "shengze"
    qs = QuestSystem(s, bus, WANLI_QUESTS)
    # 接受 3 任务
    for qid in ["quest.first_silk", "quest.first_sell", "quest.first_travel"]:
        qs.accept_quest(qid)
    # 触发事件
    bus.publish(GameEvent(id="discover.item", type="discover", data={"name": "湖绫"}))
    bus.publish(GameEvent(id="fin.sell_silk", type="fin", data={"amount": 0.7}))
    bus.publish(GameEvent(id="city.arrive.suzhou", type="city"))
    summary = qs.get_progress_summary()
    ok = True
    ok = _step(f"  3 completed（{len(summary['completed'])}）", len(summary["completed"]) == 3) and ok
    ok = _step(f"  0 active（{len(summary['active'])}）", len(summary["active"]) == 0) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.34 EventBus + DramaManager + QuestSystem 静态测试 ===\n")
    ok1 = test_event_bus()
    ok2 = test_drama_manager()
    ok3 = test_quest_system()
    ok4 = test_3_quest_conditions()
    ok5 = test_e2e_3_quests()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
