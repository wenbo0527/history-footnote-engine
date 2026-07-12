"""🆕 v2.10.1 20 回合集成测试

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P2-5
- 验证 20 回合状态机在 parse_events + apply_event + RouteDetector 协同下不崩
- 不调真实 LLM（用 mock 返回构造 LLM output）
- 使用合法 event id（基于 event_handlers.py 中 handler 接受格式）

用法: .venv/bin/python scripts/test_20rounds_integration.py
"""
import json
import sys
import time

from history_footnote.event_parser import parse_events, apply_event
from history_footnote.chapter.route_detector import (
    RouteDetector, NARRATIVE_FLOW,
)
from history_footnote.chapter.types import ChapterBlueprint, ChapterState
from history_footnote.game_state import GameState


# 20 回合剧本（使用合法 event ids）
ROUNDS = [
    # ===== 1-4 chapter1 opening =====
    {"input": "我在织机前织湖绫", "events": [], "expected": "opening"},
    {"input": "我把织好的湖绫拿到牙行去卖", "events": [
        {"id": "fin.sell_silk", "amount": "3.0", "narrative": "卖了湖绫，得银三两"}
    ], "expected": "opening"},
    {"input": "我听邻居说李秀才中了举人", "events": [
        {"id": "fam.meet.fm_son", "narrative": "我儿子讲李秀才中了举人"}
    ], "expected": "opening"},
    {"input": "我听说今年丝税要加", "events": [], "expected": "rising_conflict"},
    # ===== 5-8 chapter1 rising_conflict =====
    {"input": "我去里长那里问今年的税单", "events": [], "expected": "rising_conflict"},
    {"input": "我决定硬抗税", "events": [], "expected": "rising_conflict"},
    {"input": "我去苏州城里走走，去看看", "events": [
        {"id": "city.arrive.suzhou", "narrative": "坐船到了苏州城里"}
    ], "expected": "rising_conflict"},
    {"input": "我听说今年第一批洋船要来了", "events": [], "expected": "crisis"},
    # ===== 9-12 chapter1 crisis → convergence =====
    {"input": "我看到县衙贴出告示", "events": [], "expected": "crisis"},
    {"input": "我决定扩大织机规模，买一台织机", "events": [
        {"id": "prop.buy.shengze", "prop_id": "machine_001", "type": "machine", "name": "新织机"}
    ], "expected": "crisis"},
    {"input": "我去告官府，从盛泽来到苏州", "events": [
        {"id": "city.arrive.suzhou", "narrative": "坐船到苏州府告官"}
    ], "expected": "convergence"},
    {"input": "我听李秀才说可以借债", "events": [
        {"id": "fin.borrow", "amount": "5.0", "narrative": "向李秀才借银五两"}
    ], "expected": "convergence"},
    # ===== 13-16 chapter1 convergence → resolution =====
    {"input": "我开始织春蚕丝", "events": [
        {"id": "discover.fact.spring_silk", "narrative": "春蚕可织春丝"}
    ], "expected": "convergence"},
    {"input": "我去跟邻人商量，从盛泽起身", "events": [
        {"id": "city.leave.shengze", "narrative": "离开盛泽去邻人家"}
    ], "expected": "convergence"},
    {"input": "我修好织机", "events": [], "expected": "resolution"},
    {"input": "我用借的钱交了税，坐车回到盛泽", "events": [
        {"id": "fin.pay_tax", "amount": "2.0", "narrative": "交了二两税"},
        {"id": "city.arrive.shengze", "narrative": "坐车回到盛泽"},
    ], "expected": "resolution"},
    # ===== 17-20 chapter1 resolution =====
    {"input": "我把春蚕丝拿去卖", "events": [
        {"id": "fin.sell_silk", "amount": "8.0", "narrative": "卖春丝得银八两"}
    ], "expected": "resolution"},
    {"input": "我还了一部分债", "events": [
        {"id": "fin.repay", "amount": "3.0", "narrative": "还了部分债"}
    ], "expected": "resolution"},
    {"input": "我跟沈氏在自家织房", "events": [], "expected": "resolution"},
    {"input": "我决定继续守这片土地", "events": [
        {"id": "evt.tax.weaving_machine", "amount": "0.3", "narrative": "税单已清，织机加征 0.3 两"}
    ], "expected": "resolution"},
]


def main():
    """20 回合集成测试"""
    print("=" * 60)
    print("🆕 v2.10.1 20 回合集成测试")
    print("=" * 60)

    start_time = time.time()

    # 初始化
    state = GameState()
    # 给一些初始 family 让 fam.meet 能找到
    state.family_members.append({
        "id": "fm_wife", "name": "沈氏", "relation": "wife", "age": 27,
        "location": "shengze", "health": "healthy", "relationship_score": 70,
        "alive": True, "notes": "操持家务", "story_hooks_used": [],
    })
    state.family_members.append({
        "id": "fm_son", "name": "阿宝", "relation": "son", "age": 5,
        "location": "shengze", "health": "healthy", "relationship_score": 80,
        "alive": True, "notes": "幼子", "story_hooks_used": [],
    })
    # 初始 genealogy entry 让 gen.ancestor 可用
    state.genealogy.append({
        "id": "anc_001",
        "is_known_to_player": False,
        "location": "shengze",
    })
    chapter = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    detector = RouteDetector(llm_callable=None)

    stats = {
        "parse_total": 0,
        "parse_success": 0,
        "parse_fail": 0,
        "events_total": 0,
        "apply_success": 0,
        "apply_fail": 0,
        "route_change": 0,
        "route_no_change": 0,
        "events_by_type": {},
    }
    errors = []
    route_changes_log = []

    for round_num, round_data in enumerate(ROUNDS, 1):
        player_input = round_data["input"]
        events = round_data["events"]
        expected = round_data["expected"]

        # 1. parse_events
        stats["parse_total"] += 1
        if events:
            # 构造 LLM output
            llm_output = "<events>"
            for ev in events:
                attrs = " ".join(f'{k}="{v}"' for k, v in ev.items() if k != "id")
                llm_output += f'<event id="{ev["id"]}" {attrs} />'
            llm_output += "</events>"
            parsed = parse_events(llm_output)
            stats["parse_success"] += 1 if len(parsed) == len(events) else 0
            stats["parse_fail"] += 1 if len(parsed) != len(events) else 0
            if len(parsed) != len(events):
                errors.append(f"Round {round_num}: parse got {len(parsed)} expected {len(events)}")
        else:
            parsed = parse_events("无事件的叙事")
            stats["parse_success"] += 1 if parsed == [] else 0
            stats["parse_fail"] += 1 if parsed else 0

        # 2. apply_event 每个
        for ev in parsed:
            stats["events_total"] += 1
            result = apply_event(state, ev)
            if result:
                stats["apply_success"] += 1
            else:
                stats["apply_fail"] += 1
                errors.append(f"Round {round_num}: apply failed for {ev.get('id')}")
            ev_id = ev.get("id", "")
            domain = ev_id.split(".")[0] if "." in ev_id else "unknown"
            stats["events_by_type"][domain] = stats["events_by_type"].get(domain, 0) + 1

        # 3. RouteDetector
        value_shifts = {}
        if "抗" in player_input or "告" in player_input:
            value_shifts = {"resistance": 0.6, "tradition": -0.4}
        elif "卖" in player_input or "买" in player_input:
            value_shifts = {"trade": 0.4, "wealth": 0.2}
        elif "借" in player_input or "还" in player_input:
            value_shifts = {"debt": 0.4, "wealth": -0.2}
        elif "倭寇" in player_input or "洋船" in player_input:
            value_shifts = {"fear": 0.5, "external_threat": 0.5}
        elif "织" in player_input or "修" in player_input:
            value_shifts = {"craft": 0.3}

        anchors = []
        if "倭寇" in player_input or "洋船" in player_input:
            anchors = ["外部势力"]
        if "税" in player_input:
            anchors = ["加税"]

        result = detector.detect(
            player_input,
            value_shifts,
            chapter,
            historical_anchors_triggered=anchors,
        )
        if result["route_change"]:
            stats["route_change"] += 1
            new_template = result["suggested_template"]
            if new_template in NARRATIVE_FLOW:
                new_idx = NARRATIVE_FLOW.index(new_template)
                old_idx = NARRATIVE_FLOW.index(chapter.narrative_position)
                direction = "→" if new_idx > old_idx else "←" if new_idx < old_idx else "="
                route_changes_log.append(
                    f"Round {round_num}: {chapter.narrative_position} {direction} {new_template} (trigger: {result.get('trigger', '?')})"
                )
                if new_idx > old_idx:
                    chapter.narrative_position = new_template
        else:
            stats["route_no_change"] += 1

        state.round_number = round_num

    # === 报告 ===
    elapsed = time.time() - start_time
    print(f"\n⏱️  耗时: {elapsed:.3f} 秒")
    print(f"\n📊 parse_events:  ✅ {stats['parse_success']} / ❌ {stats['parse_fail']} (共 {stats['parse_total']} 回合)")
    print(f"📊 apply_event:   ✅ {stats['apply_success']} / ❌ {stats['apply_fail']} (共 {stats['events_total']} 事件)")
    print(f"📊 RouteDetector: 路线变化 {stats['route_change']} / 无变化 {stats['route_no_change']}")
    print(f"\n📋 事件类型分布:")
    for domain, count in sorted(stats["events_by_type"].items()):
        print(f"  {domain}: {count}")

    print(f"\n📍 章节位置变化 ({len(route_changes_log)} 次):")
    for log in route_changes_log:
        print(f"  {log}")
    print(f"\n📍 最终章节位置: {chapter.narrative_position}")
    print(f"📍 最终 round: {state.round_number}")

    if errors:
        print(f"\n❌ 错误 ({len(errors)} 个):")
        for e in errors[:15]:
            print(f"  - {e}")

    # 综合判断
    parse_rate = stats['parse_success'] / stats['parse_total'] * 100 if stats['parse_total'] else 0
    apply_rate = stats['apply_success'] / stats['events_total'] * 100 if stats['events_total'] else 0
    print(f"\n📈 成功率: parse {parse_rate:.0f}% / apply {apply_rate:.0f}%")

    if stats['parse_fail'] == 0 and stats['apply_fail'] == 0 and stats['route_change'] > 0:
        print(f"\n✅ 20 回合集成测试 全部通过 (parse 100% / apply 100% / 路线变化 {stats['route_change']} 次)")
        return 0
    elif stats['parse_fail'] == 0 and stats['apply_fail'] == 0:
        print(f"\n⚠️  解析/应用 100% 通过，但路线未变化 (应 ≥1)")
        return 1
    else:
        print(f"\n❌ 有 {stats['parse_fail'] + stats['apply_fail']} 项失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
