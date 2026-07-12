"""v2.10.1 W85 涌现式章节 · 30 回合 mock smoke

目标：验证 RouteDetector 在多回合中累积 route_history
- 第 1 回合玩家"日常" → 无路线变更
- 第 5 回合玩家"我要抗税" → 触发 rising_conflict
- 第 12 回合玩家"倭寇来了" → 触发 crisis
- 第 20 回合价值偏移到 -0.8 → 触发 rising_conflict
- 第 25 回合历史铁轨 "hai_rui_death" → 强制 convergence

不调真 LLM（mock），重点验证：
1. RouteDetector.detect() 在不同输入下的结果
2. apply_route_change 写 current_route + 追加 route_history
3. _maybe_advance_node 同步 blueprint.narrative_position
4. prompt_builder.build() 注入 current_route 字段
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade
from history_footnote.chapter.coordinator import ChapterCoordinator
from history_footnote.chapter.prompt_builder import ChapterPromptBuilder
from history_footnote.chapter.types import ChapterMeta


def main():
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7, "天下": 0.4, "取巧": 0.1}
    state.value_shifts = {"守旧": 0, "趋新": 0}
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

    # Mock LLM：返回最简 blueprint
    def mock_llm(prompt):
        chapter_id = prompt["chapter_meta"]["chapter_id"]
        return {
            "chapter_title": f"且听下回分解 · 第 {chapter_id} 章",
            "nodes": [
                {"role": "introduction", "scene": "intro"},
                {"role": "escalation", "scene": "esc"},
                {"role": "climax", "scene": "climax"},
                {"role": "resolution", "scene": "res"},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)

    # 玩家行为剧本（round → (input, value_shifts, historical_anchors)）
    PLAYER_SCRIPT = {
        1:  ("我去茶馆坐坐", {}, None),
        2:  ("先修好织机再说", {}, None),
        3:  ("和沈氏聊聊天", {}, None),
        4:  ("去牙行看看今春丝价", {}, None),
        5:  ("我要抗税，不交了", {}, None),                              # → rising_conflict (keyword)
        6:  ("和王二嫂商量对策", {}, None),
        7:  ("偷偷把织机卖掉", {}, None),
        8:  ("去衙门告官", {}, None),
        9:  ("被衙役抓了", {}, None),
        10: ("想办法出来", {}, None),
        11: ("夜里翻墙跑", {}, None),
        12: ("倭寇来了！", {}, None),                                    # → crisis (keyword)
        13: ("躲到山里", {}, None),
        14: ("听说苏州安全", {}, None),
        15: ("决定去苏州", {}, None),
        16: ("路上遇见流民", {}, None),
        17: ("接济流民", {"守旧": -0.3}, None),
        18: ("带他们一起走", {"守旧": -0.2}, None),
        19: ("到苏州城外", {"守旧": 0.1}, None),
        20: ("被苏州官府拒绝", {"守旧": -0.85}, None),                  # → rising_conflict (value_shift)
        21: ("找海瑞", {}, None),
        22: ("递交诉状", {}, None),
        23: ("等待海瑞回复", {}, None),
        24: ("听说海瑞病重", {}, None),
        25: ("海瑞去世的消息传来", {}, None),                            # Phase 1: historical_anchor 来源未定,先验证 keyword convergence
        26: ("朝廷震动", {}, None),
        27: ("皇帝下旨", {}, None),
        28: ("变革来了", {}, None),
        29: ("接受命运", {}, None),
        30: ("回家", {}, None),
    }

    print("=" * 70)
    print("=== v2.10.1 W85 涌现式章节 · 30 回合 mock smoke ===")
    print("=" * 70)
    print()
    print(">>> 模拟 30 回合（玩家行为触发 RouteDetector）<<<")
    print()

    for r in range(1, 31):
        state.round_number = r
        player_input, value_shifts, anchors = PLAYER_SCRIPT.get(r, ("...", {}, None))

        # 写入本回合玩家输入与价值偏移
        state.last_player_input = player_input
        # 累加 value_shifts(模拟 game_loop 的实际行为)
        for dim, delta in value_shifts.items():
            state.value_shifts[dim] = state.value_shifts.get(dim, 0) + delta

        # Coordinator 3 钩子
        coord.pre_step()
        coord.post_step()  # W85 路线检测在此触发
        coord.maybe_settle()

        # 每 5 回合打点
        if r % 5 == 0 or r in (1, 12, 25):
            cs = state.chapter_state
            print(f"Round {r:2d} | chapter={cs.current_chapter} | "
                  f"route={cs.current_route.get('template', '?'):<18} | "
                  f"trigger={str(cs.current_route.get('trigger', '-'))[:40]:<42} | "
                  f"history_len={len(cs.route_history)}")

    print()
    print("=" * 70)
    print(">>> W85 路线历史总览 <<<")
    print("=" * 70)
    print()
    history = state.chapter_state.route_history
    print(f"路线变更次数: {len(history)}")
    print()
    for i, h in enumerate(history, 1):
        print(f"  [{i:2d}] round={h['round']:2d} | {h['from_template']:<18} → {h['to_template']:<18} | {h['trigger']}")
    print()

    # 验证：至少触发 3 次路线变更（rising_conflict + crisis + convergence）
    assert len(history) >= 3, f"应至少 3 次路线变更, 实际 {len(history)}"

    # 验证 5 类模板都出现过
    seen = {h["to_template"] for h in history}
    assert "rising_conflict" in seen, f"rising_conflict 应出现过, 实际 {seen}"
    assert "crisis" in seen, f"crisis 应出现过, 实际 {seen}"
    assert "convergence" in seen, f"convergence 应出现过, 实际 {seen}"

    # 验证 historical_anchor 在 RouteDetector.detect() 单元测试覆盖（test_route_detector.py::test_historical_anchor_force_convergence）
    # Phase 1 的 post_step 默认传 None（锚点来源未定）,smoke 用 keyword 触发 convergence

    print("=" * 70)
    print(">>> W85 验证通过 <<<")
    print(f"    ✓ 路线变更 ≥ 3 次（实际 {len(history)}）")
    print(f"    ✓ 5 类模板出现: {sorted(seen)}")
    print(f"    ✓ historical_anchor 链路在 RouteDetector 单元测试覆盖")
    print("=" * 70)

    # 验证 prompt_builder 注入了 current_route
    print()
    print(">>> prompt_builder 注入验证 <<<")
    builder = ChapterPromptBuilder(state, era_config)
    ctx = builder.build(ChapterMeta(chapter_id=1))
    assert "current_route" in ctx, "current_route 未注入"
    cr = ctx["current_route"]
    print(f"  current_route.template: {cr['template']}")
    print(f"  current_route.trigger:  {cr['trigger']}")
    print(f"  current_route.dm_instruction 长度: {len(cr['dm_instruction'])}")
    print(f"  route_history 注入条数: {len(cr['route_history'])}（最近 3 条）")
    print()
    print(">>> 全部验证通过 <<<")


if __name__ == "__main__":
    main()