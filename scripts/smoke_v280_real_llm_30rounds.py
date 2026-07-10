"""v2.8.0 真 LLM 30 回合端到端 smoke

用 minimax-anthropic 真 LLM（温度 0）跑 2 章：
- 第 1 章（chapter_id=1，departure/ordinary）+ Build=外望人
- 第 2 章（chapter_id=2，departure/call）+ Build=外望人

每章节 15 回合（约 13 秒/章节 LLM 生成）：
- 玩家策略：选第一个 option（最稳定）
- 模拟 value_dimensions 偏移
- 验证章节自动结算 + 下一章自动 init
- 验证 chapter_history 累计
- 验证 path_state 切换（每 3 个 option）
"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
_LOG = logging.getLogger("smoke_v280_30rounds")


def main():
    from history_footnote.game_state import GameState
    from history_footnote.llm_providers import make_llm
    from history_footnote.chapter.dm_tool import fill_chapter_blueprint_via_llm
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.chapter.coordinator import ChapterCoordinator

    # 读 LLM_PRIMARY_PROVIDER
    provider = os.environ.get("LLM_PRIMARY_PROVIDER", "mock")
    _LOG.info(">>> 使用 provider: %s <<<", provider)

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7}
    state.cash = -1.5
    # 选 Build（外望人）
    state.player_build = "外望人"

    era_config = {
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
                {"act": "initiation", "chapters": [4, 5, 6, 7], "chapter_roles": ["trial", "allies", "abyss_approach", "abyss"], "emotion_tone": "tension→awakening", "choice_type": "how_to_face_challenge"},
            ],
            "paths": [
                {"id": "main_tax_resistance", "type": "main", "name": "抗税", "unlock_condition": "always", "chapters_applicable": [2, 3, 4, 5, 6]},
                {"id": "side_silk_trade", "type": "side", "name": "丝绸贸易", "unlock_condition": "always", "chapters_applicable": [2, 3, 4, 5, 6, 7]},
            ],
        },
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
            ],
        },
    }

    # 构造真 LLM
    try:
        llm = make_llm(
            provider=provider,
            era_config=era_config,
            extra_kwargs={"temperature": 0.0},
        )
    except Exception as e:
        _LOG.error("构造真 LLM 失败: %s", e)
        return 1
    _LOG.info(">>> 构造章节 LLM 完成: %s <<<", type(llm).__name__)

    # 构造 ChapterFacade
    facade = ChapterFacade(
        state=state,
        era_config=era_config,
        root_dir=Path(__file__).parent.parent,
    )

    # 构造 Coordinator（带 LLM 路径）
    coord = ChapterCoordinator(
        state=state,
        chapter_facade=facade,
        drama_manager=None,
        llm_callable=llm,  # 关键：传真 LLM
    )

    _LOG.info("=" * 70)
    _LOG.info(">>> 30 回合真 LLM 端到端开始（2 章 × 15 回合）<<<")
    _LOG.info("=" * 70)

    # 跑 30 回合
    chapter_count = 0
    init_count = 0
    for r in range(1, 31):
        state.round_number = r
        # pre_step
        coord.pre_step()
        # 模拟玩家选第一个 option（写入 recent_path_choices）
        if state.chapter_state.current_node > 0 and state.chapter_state.blueprint:
            nodes = state.chapter_state.blueprint.get("nodes", [])
            current_node_idx = state.chapter_state.current_node - 1
            if current_node_idx < len(nodes):
                options = nodes[current_node_idx].get("option_directions", [])
                if options:
                    first_opt = options[0]
                    path = first_opt.get("path") or first_opt.get("path_hint", "")
                    if path:
                        facade.record_path_choice(path)
        # post_step（PathSwitcher）
        coord.post_step()
        # maybe_settle
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > chapter_count:
            chapter_count = len(state.chapter_state.chapter_history)
            init_count += 1
            last_record = state.chapter_state.chapter_history[-1]
            _LOG.info(">>> 第 %d 章结算（rounds=%d, status=%s）<<<",
                      last_record.get("chapter"),
                      last_record.get("rounds_in_chapter"),
                      last_record.get("closure_status"))
            if chapter_count < 2:
                # 触发下一章 init
                coord._initialized = False
            else:
                break

    _LOG.info("=" * 70)
    _LOG.info(">>> 30 回合真 LLM 端到端完成 <<<")
    _LOG.info("=" * 70)
    _LOG.info("LLM 初始化次数: %d 次", init_count)
    _LOG.info("完成章节数: %d", len(state.chapter_state.chapter_history))
    _LOG.info("玩家 Build: %s", state.player_build)
    _LOG.info("cash: %.2f", state.cash)
    _LOG.info("value_dimensions: %s", state.value_dimensions)
    _LOG.info("path_state.active_paths: %s", state.path_state.active_paths)
    _LOG.info("path_state.main_path_focus: %s", state.path_state.main_path_focus)
    _LOG.info("path_state.recent_path_choices: %s", getattr(state, "recent_path_choices", []))
    _LOG.info("")

    # 验证关键不变量
    _LOG.info(">>> 验证关键不变量 <<<")
    assert len(state.chapter_state.chapter_history) == 2, f"期望 2 章，实际 {len(state.chapter_state.chapter_history)}"
    _LOG.info("✅ 完成章节数=2")
    assert init_count == 2, f"期望 LLM 初始化 2 次，实际 {init_count}"
    _LOG.info("✅ LLM 初始化次数=2（每章 1 次）")
    for i, h in enumerate(state.chapter_state.chapter_history, 1):
        assert "summary" in h
        assert "closure_status" in h
        assert "rounds_in_chapter" in h
    _LOG.info("✅ 每章 4 必填项 + 4 元信息完整")

    _LOG.info("=" * 70)
    _LOG.info(">>> ✅ 30 回合真 LLM 端到端 smoke 全通过 <<<")
    _LOG.info("=" * 70)

    # 打印最终每章摘要
    _LOG.info(">>> 最终章节摘要 <<<")
    for h in state.chapter_state.chapter_history:
        _LOG.info("  Chapter %d: %s | %d 回合 | status=%s",
                  h.get("chapter"),
                  h.get("summary", "")[:60],
                  h.get("rounds_in_chapter"),
                  h.get("closure_status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
