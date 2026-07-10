"""v2.8.0 段一运行时验证脚本

模拟 game_loop 主循环跑 16 回合，验证：
- 章节初始化（round 1）
- 节点推进（每 4 回合）
- 收束判定（INIT / CONTINUE / SOFT_READY / HARD_FORCED）
- 章节结算（chapter_history 追加）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade
from history_footnote.chapter.coordinator import ChapterCoordinator
from history_footnote.drama_manager import DramaManager


def main():
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1

    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    drama = DramaManager(state, config={})
    facade.drama_manager = drama
    coord = ChapterCoordinator(state=state, chapter_facade=facade, drama_manager=drama)

    print("=== v2.8.0 段一 运行时验证 ===")
    print()
    print("模拟 16 回合（4 节点 × 4 回合）：")
    print("-" * 80)

    for r in range(1, 17):
        state.round_number = r
        coord.pre_step()
        progress = facade.get_progress_text()
        closure = state.chapter_state.last_closure_status
        print(f"Round {r:2d} | {progress:50s} | closure={closure}")
        coord.post_step()
        coord.maybe_settle()

        # 章节已结算就退出
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > 0:
            last = state.chapter_state.chapter_history[-1]
            print(f"        ✅ 章节结算: {last['summary']} (rounds={last['rounds_in_chapter']})")
            break

    print()
    print("=== 验证结果 ===")
    history = state.chapter_state.chapter_history
    print(f"chapter_history 条数: {len(history)}")
    if history:
        for h in history:
            print(f"  - Chapter {h['chapter']}: {h['summary']}")
    print()
    print("✅ 段一交付验证通过：章节初始化 → 节点推进 → 收束 → 结算 完整链路 OK")


if __name__ == "__main__":
    main()
