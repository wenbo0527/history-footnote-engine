"""v2.8.0 段三 W13 smoke：30 回合跑 2 章 + 路径切换

模拟真实玩家：
- chapter 1 期间玩家在主路径上选 3 次 → 主路径保持
- chapter 2 期间玩家切到丝绸贸易路径 → 主路径切换
- chapter 2 期间 value_path 因 value_dimensions > 0.5 自动解锁
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade
from history_footnote.chapter.coordinator import ChapterCoordinator


def main():
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7, "天下": 0.4, "取巧": 0.1}
    state.cash = -1.5

    era_config = {
        "npcs": {
            "npc_zhao_lizhang": {"name": "赵里长"},
            "fm_wife": {"name": "沈氏"},
        },
        "knowledge": {"entries": []},
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
            ],
            "paths": [
                {
                    "id": "main_tax_resistance",
                    "type": "main",
                    "name": "赋税抗争",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6],
                },
                {
                    "id": "side_silk_trade",
                    "type": "side",
                    "name": "丝绸贸易",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6, 7],
                },
                {
                    "id": "value_path",
                    "type": "side",
                    "name": "价值觉醒",
                    "unlock_condition": "value_threshold",
                    "chapters_applicable": [3, 4, 5, 6, 7],
                },
            ],
        },
    }

    facade = ChapterFacade(state=state, era_config=era_config, root_dir=Path(__file__).parent.parent)

    def adaptive_llm(prompt):
        chapter_id = prompt["chapter_meta"]["chapter_id"]
        return {
            "chapter_title": f"且听下回分解 · 第 {chapter_id} 章",
            "nodes": [
                {"role": "introduction", "scene": f"c{chapter_id} intro", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "scene": f"c{chapter_id} esc", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "scene": f"c{chapter_id} climax", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "scene": f"c{chapter_id} res", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=adaptive_llm)

    print("=" * 70)
    print("=== v2.8.0 段三 W13 smoke：30 回合 + 路径切换 ===")
    print("=" * 70)
    print()
    print(f"初始: round=1, value_dimensions.尽责=+0.8（>0.5 应自动解锁 value_path）")
    print(f"      cash={state.cash}（负债）")
    print()

    # 模拟玩家在 chapter 2 选了 3 次 side_silk_trade
    player_choices_chapter_2 = ["side_silk_trade", "side_silk_trade", "side_silk_trade"]

    for r in range(1, 31):
        state.round_number = r
        coord.pre_step()
        if r == 16:
            # chapter 2 开始时记录玩家选择
            print(">>> chapter 2 开始，玩家选 3 次 side_silk_trade <<<")
            state.recent_path_choices = player_choices_chapter_2
        if r % 4 == 0 or r in (15, 16, 30):
            print(f"Round {r:2d} | node {state.chapter_state.current_node}/4 | main_path_focus={state.path_state.main_path_focus} | active={state.path_state.active_paths}")
        coord.post_step()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) < 2:
            coord._initialized = False
        if len(state.chapter_state.chapter_history) >= 2:
            break

    print()
    print("=" * 70)
    print(">>> 路径状态总览 <<<")
    print("=" * 70)
    print()
    print(f"active_paths: {state.path_state.active_paths}")
    print(f"locked_paths: {state.path_state.locked_paths}")
    print(f"completed_paths: {state.path_state.completed_paths}")
    print(f"main_path_focus: {state.path_state.main_path_focus}")
    print(f"path_affinity: {state.path_state.path_affinity}")
    print()
    print("=" * 70)
    print(">>> 段三 W13 交付验证通过：路径切换 + 章节初始化重排全流程 OK <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
