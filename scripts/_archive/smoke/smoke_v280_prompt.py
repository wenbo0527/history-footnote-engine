"""v2.8.0 段二 W7 smoke 验证

模拟真实场景：
1. 玩家已玩 2 章（有 chapter_history）
2. 玩家选了"抗税"+ "借债"（value_dimensions 偏移）
3. 玩家 cash = -1.5（负债）
4. 喂 LLM 的 prompt 完整可视化
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade


def main():
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 17  # 进入第 3 章

    # 模拟已结算的 2 章
    state.chapter_state.chapter_history = [
        {"chapter": 1, "summary": "春蚕上市，赋税初现，玩家选了抗税，欠牙行 1.5 两", "transition": "season"},
        {"chapter": 2, "summary": "赵里长催税，玩家借债还税", "transition": "season"},
    ]

    # 玩家画像
    state.value_dimensions = {
        "守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7, "天下": 0.4, "取巧": 0.1,
    }
    state.cash = -1.5  # 负债
    state.rice = 5.0

    # 构造 era_config（含元属性）
    era_config = {
        "npcs": {
            "npc_zhao_lizhang": {"name": "赵里长"},
            "npc_wang_sao": {"name": "王二嫂"},
            "fm_wife": {"name": "沈氏"},
            "fm_son": {"name": "阿宝"},
        },
        "knowledge": {
            "entries": [
                {"id": "kn_silk_price_1587_spring"},
                {"id": "kn_tax_pressure_wanli"},
                {"id": "kn_zhao_lizhang_role"},
                {"id": "kn_yamen_procedure"},
                {"id": "kn_shengze_market"},
            ],
        },
        "narrative": {
            "paths": [
                {"id": "main_tax_resistance"},
                {"id": "side_silk_trade"},
            ],
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
                {"act": "initiation", "chapters": [4, 5, 6, 7], "chapter_roles": ["trial", "allies", "abyss_approach", "abyss"], "emotion_tone": "tension→awakening", "choice_type": "how_to_face_challenge"},
            ],
        },
    }

    facade = ChapterFacade(state=state, era_config=era_config, root_dir=Path(__file__).parent.parent)

    # 为第 3 章构建 prompt
    print("=" * 70)
    print("=== v2.8.0 段二 W7 smoke 验证 ===")
    print("=" * 70)
    print()
    print(f"玩家状态: round={state.round_number}, cash={state.cash}（负债）, rice={state.rice}石")
    print(f"已结算章节数: {len(state.chapter_state.chapter_history)}")
    print()
    print(">>> 调用 facade.build_prompt_context(3) <<<")
    print()

    ctx = facade.build_prompt_context(3)

    # 完整打印
    print(json.dumps(ctx, ensure_ascii=False, indent=2))

    print()
    print("=" * 70)
    print(">>> 验证：模拟 LLM 输出 → convert_llm_to_blueprint <<<")
    print("=" * 70)
    print()

    # 模拟 LLM 看到 prompt 后生成的输出
    simulated_llm_output = {
        "chapter_title": "且听下回分解 · 门槛",
        "chapter_subtitle": "是进是退？",
        "transition_hint": "identity",
        "nodes": [
            {
                "index": 1,
                "role": "introduction",
                "scene": "盛泽镇夏夜，沈氏在灯下织布，阿宝睡了",
                "npc_ids": ["fm_wife", "fm_son"],
                "option_directions": [
                    {"text": "跟沈氏商量", "path": "main_tax_resistance"},
                    {"text": "独自想办法", "path": "main_tax_resistance"},
                ],
                "knowledge_ids": ["kn_shengze_market"],
            },
            {
                "index": 2,
                "role": "escalation",
                "scene": "王二嫂带来消息：可以去苏州府请愿",
                "npc_ids": ["npc_wang_sao"],
                "option_directions": [
                    {"text": "去苏州", "path": "main_tax_resistance"},
                    {"text": "留在盛泽", "path": "main_tax_resistance"},
                ],
                "knowledge_ids": ["kn_yamen_procedure"],
            },
            {
                "index": 3,
                "role": "climax",
                "scene": "赵里长得知玩家要上告",
                "npc_ids": ["npc_zhao_lizhang"],
                "option_directions": [
                    {"text": "当面对质", "path": "main_tax_resistance"},
                ],
            },
            {
                "index": 4,
                "role": "resolution",
                "scene": "玩家踏上离乡路",
                "npc_ids": [],
            },
        ],
    }

    blueprint = facade.convert_llm_to_blueprint(simulated_llm_output, chapter_id=3)

    print(f"✅ Blueprint 生成成功")
    print(f"   - chapter_id: {blueprint.chapter_id}")
    print(f"   - title: {blueprint.chapter_title}")
    print(f"   - meta.act: {blueprint.meta.act}")
    print(f"   - meta.role: {blueprint.meta.role}")
    print(f"   - meta.emotion_tone: {blueprint.meta.emotion_tone}")
    print(f"   - nodes: {len(blueprint.nodes)} 个")
    print(f"   - transition: {blueprint.transition_hint}")
    print()
    print("=== smoke 验证通过：prompt 构建 → LLM 输出 → 引擎 Blueprint 端到端 OK ===")


if __name__ == "__main__":
    main()
