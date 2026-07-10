"""v2.8.0 段六 W18+ smoke：真 LLM 跑章节蓝图生成

用 LLM_PRIMARY_PROVIDER 配置的真实 LLM（温度 0）生成章节蓝图：
1. build prompt
2. invoke 真 LLM
3. parse JSON output
4. validate + fallback
5. Build 分化（如果 player_build 设定）
6. 写入 state.chapter_state
"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 详细日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
_LOG = logging.getLogger("smoke_v280_real_llm")


def main():
    from history_footnote.game_state import GameState
    from history_footnote.llm_providers import make_llm_for_purpose, make_llm
    from history_footnote.chapter.dm_tool import fill_chapter_blueprint_via_llm
    from history_footnote.sub_facades import ChapterFacade

    # 读 LLM_PRIMARY_PROVIDER（env 变量）
    provider = os.environ.get("LLM_PRIMARY_PROVIDER", "mock")
    _LOG.info(">>> 使用 provider: %s <<<", provider)

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7}
    state.cash = -1.5
    # 选 Build（外望人 / 守乡人）
    state.player_build = "外望人"

    era_config = {
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
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
            ],
        },
    }

    # 构造真 LLM
    try:
        llm = make_llm(
            provider=provider,
            era_config=era_config,
            extra_kwargs={"temperature": 0.0},  # 章节制温度 0
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

    # 真 LLM 生成章节蓝图
    _LOG.info(">>> invoke 真 LLM 生成章节蓝图 (chapter_id=1) <<<")
    try:
        blueprint = fill_chapter_blueprint_via_llm(
            state=state,
            chapter_id=1,
            era_config=era_config,
            llm_callable=llm,
            chapter_facade=facade,
        )
    except Exception as e:
        _LOG.error("真 LLM 调用失败: %s", e)
        return 1

    if blueprint is None:
        _LOG.error("Blueprint 为 None，fallback 也失败")
        return 1

    # 打印结果
    _LOG.info("=" * 70)
    _LOG.info(">>> 章节蓝图生成成功 <<<")
    _LOG.info("=" * 70)
    _LOG.info("chapter_id: %d", blueprint.chapter_id)
    _LOG.info("chapter_title: %s", blueprint.chapter_title)
    _LOG.info("chapter_subtitle: %s", blueprint.chapter_subtitle)
    _LOG.info("transition_hint: %s", blueprint.transition_hint)
    _LOG.info("meta.act: %s", blueprint.meta.act)
    _LOG.info("meta.role: %s", blueprint.meta.role)
    _LOG.info("meta.emotion_tone: %s", blueprint.meta.emotion_tone)
    _LOG.info("nodes (%d 个):", len(blueprint.nodes))
    for i, node in enumerate(blueprint.nodes, 1):
        _LOG.info("  Node %d: role=%s", i, node.role)
        _LOG.info("    scene: %s", node.scene[:80] + "..." if len(node.scene) > 80 else node.scene)
        _LOG.info("    npc_ids: %s", node.npc_ids)
        _LOG.info("    options: %d 个", len(node.option_directions))

    # 验证 Build 分化（state.player_build = "外望人"）
    _LOG.info("=" * 70)
    _LOG.info(">>> Build 分化验证（player_build=外望人）<<<")
    _LOG.info("=" * 70)
    for i, node in enumerate(blueprint.nodes, 1):
        if "外望人" in node.scene or "河西" in node.scene or "春市" in node.scene:
            _LOG.info("  ✅ Node %d 含外望人分化标识", i)
        else:
            _LOG.info("  ○  Node %d 未含外望人分化（保持默认）", i)

    _LOG.info("=" * 70)
    _LOG.info(">>> ✅ 真 LLM 章节蓝图生成 smoke 通过 <<<")
    _LOG.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
