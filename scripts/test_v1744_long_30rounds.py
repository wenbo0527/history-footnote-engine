"""🆕 v1.7.44 长程验证（30 轮真实 LLM）

目标：
- 30 轮覆盖月度结算 ×10
- 触发 1601 葛贤抗税（evt.guoben_dispute）
- 统计 LLM Cache 命中
- 统计 Drama 干预触发
- 统计 QuestSystem 完成
- 统计事件反馈
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
    log_path = Path("logs/test_v1744_long_30rounds.log")
    log = open(log_path, "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 70)
    L("v1.7.44 长程验证：30 轮真实 LLM（含 1601 葛贤抗税）")
    L("=" * 70)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1744_"))
    save = SaveManager(tmp)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save,
        selected_identity="weaving_male",
    )
    game.state.cash = 5.0
    game.state.rice = 8.0
    game.state.debt = 1.0
    game.state.monthly_burn = 1.2
    game.state.add_property("shengze", {"id": "p1", "type": "shop", "name": "织房", "value": 15, "rent_per_month": 0.3})
    game.state.add_family_member({"id": "fm_wife", "name": "沈氏", "relation": "wife", "location": "shengze"})

    L(f"\n初始: cash={game.state.cash:.2f}, rice={game.state.rice:.1f}, debt={game.state.debt:.2f}")

    # 30 轮输入：覆盖
    # - Round 1-5: 织绸/卖绸（盛泽日常）
    # - Round 6-10: 城市旅行（苏州/杭州/松江）
    # - Round 11-15: 日常（算账/见人/借款）
    # - Round 16-20: 1587 月度结算
    # - Round 21-25: 1592-1598 朝鲜之役传闻
    # - Round 26-29: 1601 葛贤抗税
    # - Round 30: 后葛贤时代
    inputs = [
        # Round 1-5: 织绸/卖绸日常
        "我织了一匹湖绫，丝光莹润。",
        "我去镇上牙行卖这匹湖绫，得银七钱。",
        "我又织了一匹湖绫。",
        "我又去牙行卖第二匹。",
        "我算了算账，还了五钱借款。",
        # Round 6-10: 城市旅行
        "我搭船去苏州阊门码头。",
        "在苏州，我找了家茶馆坐坐，听说朝鲜打仗。",
        "我又搭船去杭州。",
        "在西湖边看丝市行情。",
        "我回盛泽。",
        # Round 11-15: 日常
        "我见沈氏。",
        "我又织了一匹湖绫。",
        "我又去牙行卖。",
        "借了邻居老王三两银子买米。",
        "我又去茶馆听人聊朝鲜之役。",
        # Round 16-20: 1587 月度结算 + 日常
        "我交了税款三钱。",
        "我又织了一匹湖绫。",
        "我又去牙行卖。",
        "在盛泽镇上转转。",
        "我算了算账。",
        # Round 21-25: 朝鲜之役传闻
        "听说朝鲜打完了，朝廷要加税。",
        "我交了这个月的税款。",
        "我在茶馆听人议论时局。",
        "我又织了一匹湖绫，存着不卖。",
        "时间过了几年，听说西北有旱灾。",
        # Round 26-30: 1601 葛贤抗税
        "时间到了 1601 年，阊门的织工在闹事。",
        "我想去苏州看看织工们的动静。",
        "我在茶馆听张婶说葛贤被抓了。",
        "我回到盛泽，继续织绸。",
        "我算了算这十年的家底。",
    ]

    # 强制推进日期（模拟时间流逝）
    forced_dates = {
        # Round 16 强制 1587-08（触发月度结算）
        16: "1587年8月",
        # Round 21 强制 1592-06（朝鲜之役开始）
        21: "1592年6月",
        # Round 25 强制 1600-12
        25: "1600年12月",
        # Round 26 强制 1601-06（葛贤抗税）
        26: "1601年6月",
        # Round 30 强制 1605-12
        30: "1605年12月",
    }

    # 统计
    cache_hits = []
    perf_snapshots = []
    intervention_history = []
    events_history = []

    t0 = time.time()
    for i, inp in enumerate(inputs, 1):
        # 强制推进日期
        if i in forced_dates:
            old_date = game.state.current_date
            game.state.current_date = forced_dates[i]
            L(f"\n--- Round {i} | {inp} ---")
            L(f"  📅 强制推进日期: {old_date} → {game.state.current_date}")
        else:
            L(f"\n--- Round {i} | {inp} ---")

        t_round = time.time()
        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            L(f"  ❌ 失败: {e}")
            continue
        t_round = time.time() - t_round

        # 收集数据
        items = list(game.state.discoveries.get("items", {}).values())
        persons = list(game.state.discoveries.get("persons", {}).values())
        places = list(game.state.discoveries.get("places", {}).values())
        n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
        n_guoben = any("葛贤" in (n.get("narrative", "") if isinstance(n, dict) else "") for n in game.state.narrative_history)
        events_for_display = game.engine.get_recent_events_for_display(limit=5)

        # 性能
        perf = game.engine.get_extended_perf_stats()
        cache_stats = perf.get("wiki_cache", {})

        L(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, city={game.state.current_city}")
        L(f"  discoveries: items={len(items)}, persons={len(persons)}, places={len(places)}")
        L(f"  triggered_events: {len(game.state.triggered_events)}")
        L(f"  monthly_settle: {n_settle} 次")
        L(f"  narrative 含'葛贤': {n_guoben}")
        L(f"  perf: llm.calls={perf['llm']['calls']}, llm.avg_ms={perf['llm']['avg_ms']:.0f}")
        L(f"  cache: size={cache_stats.get('cache_size', 0)}, hit={cache_stats.get('hit_rate', 0):.0%}")
        L(f"  轮耗时: {t_round:.1f}s")

        cache_hits.append(cache_stats.get("hit_rate", 0))
        perf_snapshots.append(perf.copy())
        intervention_history.append(list(game.drama_manager.intervention_history))
        events_history.append(events_for_display)

    elapsed = time.time() - t0

    L(f"\n\n{'='*70}")
    L(f"📊 v1.7.44 长程验证报告（30 轮）")
    L(f"{'='*70}")

    # 1. QuestSystem
    L(f"\n[1] QuestSystem 自动完成度")
    qs = game.engine.get_quest_summary()
    L(f"  完成: {len(qs['completed'])}/{qs['total']}")
    for c in qs["completed"]:
        L(f"    ✅ {c['name']}")

    # 2. EventBus + 触发事件
    L(f"\n[2] 触发事件统计")
    L(f"  triggered_events 总数: {len(game.state.triggered_events)}")
    for ev in game.state.triggered_events[:10]:
        L(f"    - {ev}")
    if len(game.state.triggered_events) > 10:
        L(f"    ... +{len(game.state.triggered_events) - 10} more")

    # 3. 1601 葛贤抗税
    L(f"\n[3] 1601 葛贤抗税验证")
    n_guoben_total = sum(1 for n in game.state.narrative_history
                         if isinstance(n, dict) and "葛贤" in n.get("narrative", ""))
    L(f"  narrative 含'葛贤'条数: {n_guoben_total}")
    L(f"  {'✅ 触发' if n_guoben_total > 0 else '❌ 未触发'}")

    # 4. 月度结算
    L(f"\n[4] 月度结算次数")
    n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
    L(f"  monthly_settle 触发: {n_settle} 次")
    L(f"  期望（4 年每月结算）: 约 36 次")

    # 5. DramaManager
    L(f"\n[5] DramaManager 干预统计")
    L(f"  总干预次数: {len(game.drama_manager.intervention_history)}")
    type_counts = {}
    for iv in game.drama_manager.intervention_history:
        t = iv.get("type", "")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, n in type_counts.items():
        L(f"    {t}: {n} 次")

    # 6. Wiki cache
    L(f"\n[6] Wiki Cache 长期统计")
    cache_stats = game.engine.get_wiki_cache_stats()
    L(f"  cache_size: {cache_stats['cache_size']}")
    L(f"  hit_rate: {cache_stats['hit_rate']:.0%}")
    L(f"  cache_max: {cache_stats['cache_max']}")

    # 7. LLM 性能
    L(f"\n[7] LLM 性能")
    final_perf = game.engine.get_extended_perf_stats()
    L(f"  总 LLM 调用: {final_perf['llm']['calls']}")
    L(f"  总 LLM 耗时: {final_perf['llm']['total_ms']:.0f}ms ({final_perf['llm']['total_ms']/1000:.1f}s)")
    L(f"  平均/调用: {final_perf['llm']['avg_ms']:.0f}ms")

    # 8. EventBus
    L(f"\n[8] EventBus 统计")
    bs = game.engine.event_bus.get_stats()
    L(f"  总发布: {bs['total_published']}")
    L(f"  总处理: {bs['total_handled']}")
    L(f"  失败: {bs['total_failed']}")
    L(f"  死信: {bs['dead_letter_count']}")

    # 9. 总耗时
    L(f"\n[9] 总耗时")
    L(f"  总耗时: {elapsed:.1f}s")
    L(f"  平均/轮: {elapsed/len(inputs):.1f}s")
    L(f"  对比 v1.7.40 5 轮 172.3s（34.5s/轮）")

    # 10. 财务
    L(f"\n[10] 财务")
    L(f"  cash: 5.00 → {game.state.cash:.2f} ({(game.state.cash-5.0):+.2f})")
    L(f"  rice: 8.0 → {game.state.rice:.1f} ({(game.state.rice-8.0):+.1f})")
    L(f"  debt: 1.00 → {game.state.debt:.2f} ({(game.state.debt-1.0):+.2f})")

    # 11. event 反馈（recent）
    L(f"\n[11] 最近事件反馈")
    for e in game.engine.get_recent_events_for_display(limit=5):
        L(f"  {e.get('icon', '?')} {e.get('type', '?')}: {e.get('name', '')}")

    log.close()
    print(f"\n📄 报告写入 {log_path}")


if __name__ == "__main__":
    main()
