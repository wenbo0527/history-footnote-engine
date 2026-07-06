"""🆕 v1.7.36 优化验证（真实 LLM 跑 10 轮）

优化 3 项：
1. DramaManager 阈值 0.7→0.9 + cooldown 3 轮 + 任务模式判定
2. Prompt 显式提示 drama_hint / action_context / calendar_events
3. DM Agent state_ref 加 drama_hint 占位

验证：
- DramaManager 干预应 ≤ 3 次（不是 10）
- QuestSystem 仍 4/4 完成
- narrative_history 中是否有 hint 触发证据
"""
import io
import json
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    from history_footnote.game_loop import GameLoop
    from history_footnote.llm_providers import make_llm
    from history_footnote.storage.save_manager import SaveManager

    Path("logs").mkdir(exist_ok=True)
    log_path = Path("logs/test_v1736_real_llm_10rounds.log")
    log = open(log_path, "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("v1.7.36 真实 LLM 跑 10 轮（优化验证）")
    L("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1736_"))
    save = SaveManager(tmp)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save,
        selected_identity="weaving_male",
    )
    game.state.cash = 5.0
    game.state.rice = 5.0
    game.state.debt = 1.0
    game.state.monthly_burn = 1.2
    game.state.add_property("shengze", {"id": "p1", "type": "shop", "name": "织房", "value": 15, "rent_per_month": 0.3})
    game.state.add_family_member({"id": "fm_wife", "name": "沈氏", "relation": "wife", "location": "shengze"})

    inputs = [
        "我织了一匹湖绫，丝光莹润。",
        "我去镇上牙行卖这匹湖绫。",
        "我又织了一匹湖绫，纬线均匀。",
        "我又去牙行卖第二匹。",
        "我搭船去苏州阊门码头。",
        "在苏州，我找了家茶馆坐坐。",
        "我回家告诉沈氏这事。",
        "我算了算账。",
        "我又织了一匹湖绫。",
        "我又去牙行卖第三匹。",
    ]

    t0 = time.time()
    for i, inp in enumerate(inputs, 1):
        L(f"\n--- Round {i} ---")
        L(f"  input: {inp}")
        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            L(f"  ❌ 失败: {e}")
            continue

        items = list(game.state.discoveries.get("items", {}).values())
        summary = game.quest_system.get_progress_summary()
        bs = game.event_bus.get_stats()
        pm = game.drama_manager.player_model

        L(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, city={game.state.current_city}")
        L(f"  items={len(items)}, completed={len(summary['completed'])}")
        L(f"  bus: pub={bs['total_published']} fail={bs['total_failed']}")
        L(f"  drama: ir={pm.initiative_ratio:.0%}, focus={pm.current_focus}, Interventions_total={len(game.drama_manager.intervention_history)}")
        # 最新一次 intervention
        if game.drama_manager.intervention_history:
            last_iv = game.drama_manager.intervention_history[-1]
            L(f"  最新干预: Round {last_iv['round']} {last_iv['type']}")

    elapsed = time.time() - t0

    # 评估
    L(f"\n{'='*60}")
    L(f"📊 v1.7.36 优化效果评估")
    L(f"{'='*60}")

    # 对比 v1.7.35
    L(f"\n[1] DramaManager 干预次数对比")
    L(f"  v1.7.35 (10 轮): 10 次 drama_pause")
    L(f"  v1.7.36 (10 轮): {len(game.drama_manager.intervention_history)} 次")
    improvement = 10 - len(game.drama_manager.intervention_history)
    L(f"  减少: {improvement} 次 ({(improvement/10*100):.0f}%)")

    L(f"\n[2] QuestSystem 完成度")
    final_summary = game.quest_system.get_progress_summary()
    L(f"  v1.7.35: 4/4 (100%)")
    L(f"  v1.7.36: {len(final_summary['completed'])}/{final_summary['total']}")

    L(f"\n[3] EventBus 事件流")
    final_bs = game.event_bus.get_stats()
    L(f"  总发布: {final_bs['total_published']}")
    L(f"  总处理: {final_bs['total_handled']}")
    L(f"  失败: {final_bs['total_failed']}")

    L(f"\n[4] 财务")
    L(f"  cash: 5.00 → {game.state.cash:.2f}")
    L(f"  debt: 1.00 → {game.state.debt:.2f}")

    L(f"\n[5] 耗时")
    L(f"  v1.7.35: 434.1s")
    L(f"  v1.7.36: {elapsed:.1f}s")

    # 验证 prompt 修复
    L(f"\n[6] Prompt 修复验证")
    prompt_src = (ROOT / "src/history_footnote/dm/prompts/system_base.md").read_text(encoding="utf-8")
    has_drama = "DramaManager 干预 hint" in prompt_src
    has_action = "action_context hint" in prompt_src
    has_calendar = "calendar_events hint" in prompt_src
    L(f"  drama_hint 在 prompt: {has_drama}")
    L(f"  action_context 在 prompt: {has_action}")
    L(f"  calendar_events 在 prompt: {has_calendar}")
    L(f"  全部齐全: {has_drama and has_action and has_calendar}")

    # 验证 drama_manager 修复
    dm_src = (ROOT / "src/history_footnote/drama_manager.py").read_text(encoding="utf-8")
    has_09 = "TENSE_THRESHOLD = 0.9" in dm_src
    has_cooldown = "INTERVENTION_COOLDOWN" in dm_src
    has_work_pattern = "WORK_PATTERN_VERBS" in dm_src
    L(f"  DramaManager threshold 0.9: {has_09}")
    L(f"  cooldown: {has_cooldown}")
    L(f"  work pattern 跳过: {has_work_pattern}")

    log.close()
    print(f"\n📄 报告写入 {log_path}")


if __name__ == "__main__":
    main()
