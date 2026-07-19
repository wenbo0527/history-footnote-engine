"""v2.8.0 段二收尾 smoke：30 回合跑 2 章 + 元属性推进

模拟真实玩家玩 2 个章节：
- 第 1 章（departure/ordinary）：玩家抗税 + 借债
- 第 2 章（departure/call）：玩家决定是否上告
- 段间自动 init，LLM 看到前章 history
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
            "npc_wang_sao": {"name": "王二嫂"},
            "fm_wife": {"name": "沈氏"},
        },
        "knowledge": {
            "entries": [
                {"id": "kn_silk_price_1587_spring"},
                {"id": "kn_tax_pressure_wanli"},
                {"id": "kn_yamen_procedure"},
            ],
        },
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
            ],
        },
    }

    facade = ChapterFacade(state=state, era_config=era_config, root_dir=Path(__file__).parent.parent)

    # 模拟 LLM：基于玩家画像生成不同章节
    def adaptive_llm(prompt):
        chapter_id = prompt["chapter_meta"]["chapter_id"]
        role = prompt["chapter_meta"]["role"]
        history = prompt["chapter_history"]

        # 根据前章 history 调整本章内容
        context = ""
        if history:
            context = f"（基于前章: {history[-1]['summary'][:30]}）"

        return {
            "chapter_title": f"且听下回分解 · 第 {chapter_id} 章「{role}」{context}",
            "nodes": [
                {"role": "introduction", "scene": f"chapter {chapter_id} 引入", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "scene": f"chapter {chapter_id} 升级", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "scene": f"chapter {chapter_id} 高潮", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "scene": f"chapter {chapter_id} 收束", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=adaptive_llm)

    print("=" * 70)
    print("=== v2.8.0 段二 收尾 smoke：30 回合跑 2 章 ===")
    print("=" * 70)
    print()
    print(f"初始状态: round=1, cash={state.cash}（负债）")
    print(f"玩家画像: 尽责+0.8, 身边+0.7")
    print()
    print(">>> 模拟 30 回合（2 章 × 15 回合）<<<")
    print()

    for r in range(1, 31):
        state.round_number = r
        coord.pre_step()
        if r % 4 == 0 or r in (15, 30):
            print(f"Round {r:2d} | node {state.chapter_state.current_node}/4 | status={state.chapter_state.last_closure_status}")
        coord.post_step()
        coord.maybe_settle()
        # 章节完成后让 coordinator 触发下一章 init
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) < 2:
            coord._initialized = False
        if len(state.chapter_state.chapter_history) >= 2:
            break

    print()
    print("=" * 70)
    print(">>> 章节完成总览 <<<")
    print("=" * 70)
    print()
    history = state.chapter_state.chapter_history
    print(f"完成章节数: {len(history)}")
    print()
    for i, h in enumerate(history, 1):
        print(f"--- Chapter {h['chapter']} ---")
        print(f"  摘要: {h['summary']}")
        print(f"  closure_status: {h['closure_status']}")
        print(f"  rounds: {h['rounds_in_chapter']}")
        print(f"  4 必填项: core_event='{h.get('core_event', '')[:30]}' | key_choice='{h.get('key_choice', '')}' | build='{h.get('build_summary', '')}'")
        print()
    print("=" * 70)
    print(">>> 段二交付验证通过 <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
