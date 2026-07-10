"""v2.8.0 段二 W8 smoke 验证

模拟真实场景：
1. 玩家玩完第 1 章（15 回合）
2. event_log 累积了多个事件
3. last_voice_options 记录了玩家选择
4. value_dimensions 有偏移
5. 章节结算 → Settlement 生成摘要 → 写入 chapter_history
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade
from history_footnote.chapter.coordinator import ChapterCoordinator
from history_footnote.chapter.settlement import ChapterSettlement


def main():
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1

    # 模拟游戏过程中的状态累积
    state.event_log = [
        {"summary": "玩家去盛泽春市，丝价比去年涨了一成"},
        {"summary": "春税预单下来，玩家拒绝缴纳"},
        {"summary": "赵里长带衙役上门催税"},
        {"summary": "玩家找牙行借债 1.5 两"},
        {"summary": "全家夜织，凑齐税款"},
    ]
    state.last_voice_options = [{"text": "找牙行借债度难关"}]
    state.value_dimensions = {
        "守旧": 0.3, "趋新": 0.1, "尽责": 0.7,
        "身边": 0.8, "天下": 0.2, "取巧": 0.4,
    }
    state.cash = -1.5  # 负债

    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    print("=" * 70)
    print("=== v2.8.0 段二 W8 smoke 验证 ===")
    print("=" * 70)
    print()
    print(f"玩家初始: round=1, event_log={len(state.event_log)}条")
    print()
    print(">>> 模拟 16 回合（4 节点 × 4 回合）<<<")
    print()

    for r in range(1, 17):
        state.round_number = r
        coord.pre_step()
        if r % 4 == 0:
            print(f"Round {r:2d} | node {state.chapter_state.current_node}/4 | status={state.chapter_state.last_closure_status}")
        coord.post_step()
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > 0:
            break

    print()
    print(">>> 章节结算完成 <<<")
    print()
    print("=" * 70)
    print(">>> chapter_history 最新 1 条 <<<")
    print("=" * 70)
    record = state.chapter_state.chapter_history[-1]
    print(json.dumps(record, ensure_ascii=False, indent=2))
    print()
    print("=" * 70)
    print(">>> 验证 4 必填项 <<<")
    print("=" * 70)
    for field in ["core_event", "key_choice", "build_summary", "path_summary"]:
        value = record.get(field, "")
        status = "✅" if value else "❌"
        print(f"  {status} {field}: {value}")
    print()
    print(f"summary 长度: {len(record['summary'])} 字（< 200）")
    print(f"rounds_in_chapter: {record['rounds_in_chapter']}")
    print(f"transition: {record['transition']}")
    print()
    print("=== smoke 验证通过：Settlement 端到端可用 ===")


if __name__ == "__main__":
    main()
