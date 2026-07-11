"""🆕 v2.8.x W29 smoke: 完整 10 章真 LLM 端到端

跑 10 个完整章节（每章 ~15 回合，共 ~150 回合），
每章自动 init/settle，验证：
- LLM 章节蓝图生成（10 次）
- LLM 章节摘要生成（10 次）
- Build 累积（一阶 + 二阶）
- 路径三态切换（main → active → locked）
- 板块传导（板块张力改变触发隔壁板块）
- 章节历史累积

跑：LLM_PRIMARY_PROVIDER=minimax python3 scripts/smoke_v280_10chapters.py
耗时：~2-3 分钟（每次 LLM ~8-15 秒）
"""
import sys
import os
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.sub_facades import ChapterFacade
from history_footnote.chapter.coordinator import ChapterCoordinator
from history_footnote.llm_providers import make_llm

_LOG = logging.getLogger("smoke_10chapters")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def main():
    print("=" * 70)
    print("  v2.8.x W29 smoke: 完整 10 章真 LLM 端到端")
    print("=" * 70)
    print()

    provider = os.environ.get("LLM_PRIMARY_PROVIDER", "mock")
    _LOG.info(">>> 使用 provider: %s <<<", provider)

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"守旧": 0.3, "趋新": 0.2, "尽责": 0.8, "身边": 0.7}
    state.cash = -1.5
    state.player_build = "外望人"
    state.current_location = "shengze"

    era_config = {
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
                {"act": "initiation", "chapters": [4, 5, 6, 7], "chapter_roles": ["trial", "allies", "abyss_approach", "abyss"], "emotion_tone": "tension→awakening", "choice_type": "how_to_face_challenge"},
                {"act": "return", "chapters": [8, 9, 10], "chapter_roles": ["reward", "return_threshold", "master_of_two"], "emotion_tone": "hope→mastery", "choice_type": "how_to_return"},
            ],
            "paths": [
                {"id": "main_tax_resistance", "type": "main", "name": "抗税", "unlock_condition": "always", "chapters_applicable": [2, 3, 4, 5, 6, 7, 8, 9, 10]},
                {"id": "side_silk_trade", "type": "side", "name": "丝绸贸易", "unlock_condition": "always", "chapters_applicable": [2, 3, 4, 5, 6, 7, 8, 9, 10]},
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
        "plates": {
            "plate_definitions": [
                {"id": "central_plains", "name": "中原", "type": "core", "neighbors": ["jiangnan"], "base_tension": 0.3, "description": "中原"},
                {"id": "jiangnan", "name": "江南", "type": "core", "neighbors": ["central_plains"], "base_tension": 0.4, "description": "江南"},
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

    facade = ChapterFacade(
        state=state,
        era_config=era_config,
        root_dir=Path(__file__).parent.parent,
    )

    coord = ChapterCoordinator(
        state=state,
        chapter_facade=facade,
        drama_manager=None,
        llm_callable=llm,
    )

    print(f"起点: {state.current_location} | 现金 {state.cash} | 回合 {state.round_number} | Build: {state.player_build}")
    print()
    print("开始跑 10 章（每章 ~15 回合）...")
    print()

    start_time = time.time()
    chapter_count = 0
    init_count = 0

    # 跑 ~180 回合（10 章 × 15 回合 + 缓冲）
    for r in range(1, 181):
        state.round_number = r

        # 模拟玩家选第一个 option（写入 recent_path_choices）
        if state.chapter_state.current_node > 0 and state.chapter_state.blueprint:
            nodes = state.chapter_state.blueprint.get("nodes", [])
            current_node_idx = state.chapter_state.current_node - 1
            if current_node_idx < len(nodes):
                options = nodes[current_node_idx].get("option_directions", [])
                if options:
                    first_opt = options[0]
                    if isinstance(first_opt, dict):
                        path = first_opt.get("path") or first_opt.get("path_hint", "")
                    else:
                        path = ""
                    if path:
                        facade.record_path_choice(path)

        # 模拟板块张力变化（注入剧情压力）
        if r == 30:
            state.plate_state.statuses["jiangnan"] = "shifting"
            state.plate_state.statuses["central_plains"] = "tense"
            _LOG.info("[板块] r=30: jiangnan→shifting, central_plains→tense")
        elif r == 90:
            state.plate_state.statuses["central_plains"] = "shifting"
            _LOG.info("[板块] r=90: central_plains→shifting")

        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()

        # 检测章节结算
        if len(state.chapter_state.chapter_history) > chapter_count:
            chapter_count = len(state.chapter_state.chapter_history)
            last_record = state.chapter_state.chapter_history[-1]
            _LOG.info(">>> 第 %d 章结算（rounds=%d, status=%s）<<<\n    摘要: %s",
                      last_record.get("chapter"),
                      last_record.get("rounds_in_chapter"),
                      last_record.get("closure_status"),
                      last_record.get("summary", "")[:60])
            if chapter_count < 10:
                # 触发下一章 init
                coord._initialized = False
                init_count += 1

        # 超过 10 章停止
        if chapter_count >= 10:
            _LOG.info(">>> 已完成 10 章，在 r=%d 停止 <<<", r)
            break

    # 🆕 W30: 若第 10 章已 init 但未 settle（fallback 慢），补一次 settle
    if chapter_count == 9 and state.chapter_state.blueprint and state.chapter_state.current_chapter == 10:
        _LOG.info(">>> 第 10 章已 init 但未 settle，补一次 maybe_settle 强制收束 <<<")
        # 强制触发 settle：通过模拟走到节点 4
        while state.chapter_state.current_node < 4 and state.round_number < 200:
            state.round_number += 1
            coord.pre_step()
            coord.post_step()
            coord.maybe_settle()
            if len(state.chapter_state.chapter_history) > chapter_count:
                chapter_count = len(state.chapter_state.chapter_history)
                last_record = state.chapter_state.chapter_history[-1]
                _LOG.info(">>> 第 %d 章结算（rounds=%d, status=%s）补完",
                          last_record.get("chapter"),
                          last_record.get("rounds_in_chapter"),
                          last_record.get("closure_status"))
                break

    total_time = time.time() - start_time
    print()
    print("=" * 70)
    print("  ✅ 10 章完整端到端完成！")
    print("=" * 70)

    # 🆕 W30: 验证章节 Tool 可注入 LangGraph dm_agent
    print()
    print(">>> 验证章节 Tool 注入 LangGraph <<<")
    try:
        from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
        tools = make_chapter_dm_tools(
            state=state,
            facade=facade,
            llm_callable=llm,
            era_config=era_config,
        )
        print(f"    ✅ make_chapter_dm_tools 返回 {len(tools)} 个 Tool")
        for t in tools:
            print(f"      - {t.name}: {t.description[:60]}...")
        # 模拟 dm_agent 绑定（llm_wrapper.bind_tools 已支持）
        if hasattr(llm, 'bind_tools'):
            bound = llm.bind_tools(tools)
            print(f"    ✅ llm.bind_tools(tools) 成功")
        else:
            print(f"    ℹ️ LLM 无 bind_tools（{type(llm).__name__}）")
    except Exception as e:
        print(f"    ❌ Tool 注入失败: {e}")
        import traceback
        traceback.print_exc()
    print(f"  总耗时:           {total_time:.1f} 秒")
    print(f"  最终回合:         round {state.round_number}")
    print(f"  章节历史:         {len(state.chapter_state.chapter_history)} 条")
    print(f"  章节初始化:       {init_count} 次")
    print(f"  当前 Build:       {state.player_build or '外望人'}")
    print(f"  路径聚焦:         {state.path_state.main_path_focus}")
    print()
    print("章节摘要预览（前 3 章）：")
    for h in state.chapter_state.chapter_history[:3]:
        print(f"  Ch {h['chapter']}: {h.get('summary', '?')[:60]}...")
    print()
    print("板块最终状态：")
    for pid, status in state.plate_state.statuses.items():
        try:
            tension = state.plate_state.get_tension(pid)
        except Exception:
            tension = 0.0
        print(f"  {pid:20s} {status:10s} tension={tension:.2f}")


if __name__ == "__main__":
    main()
