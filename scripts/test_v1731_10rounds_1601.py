"""🆕 v1.7.31 真实 LLM 跑 10 轮 + 跑到 1601 验证葛贤抗税 + token 报告

用真实 LLM（minimax-anthropic）跑 10 轮：
- Round 1-3: 盛泽织绸
- Round 4-5: 去苏州
- Round 6: 回盛泽 + 月度结算
- Round 7-9: 日常 + 推进时间
- Round 10: 检查 1601 葛贤抗税（强制推进时间到 1601 年）

Layer 2 增强后，期望 discover.* / city.* / fam.* 触发率提升。
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
    from history_footnote.llm_wrapper import get_usage_logger

    Path("logs").mkdir(exist_ok=True)
    log = open("logs/test_v1731_10rounds_1601.log", "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("v1.7.31 真实 LLM 跑 10 轮 + 1601 葛贤抗税 + token 报告")
    L("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1731_"))
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

    L(f"\n初始: cash={game.state.cash:.2f}, rice={game.state.rice:.1f}, debt={game.state.debt:.2f}")

    inputs = [
        "我织了一匹湖绫，丝光莹润。",
        "我去镇上牙行卖这匹湖绫。",
        "我搭船去苏州。",
        "在苏州阊门码头，我找了家茶馆坐坐。",
        "苏州的丝绸生意不好做，我回盛泽。",
        "我回盛泽后，沈氏在灶上热米汤。",
        "我算算家里的账。",
        "我织了第二匹湖绫。",
        "我又去牙行卖了第二匹。",
        "时间过了好几年，到 1601 年了，听说织工在闹事。",
    ]

    # 强制把最后一轮的日期设到 1601
    initial_date = game.state.current_date
    L(f"\n初始日期: {initial_date}")

    t0 = time.time()
    for i, inp in enumerate(inputs, 1):
        # Round 10 强制推进日期
        if i == 10:
            game.state.current_date = "1601年6月"
            L(f"  🔄 Round 10 强制推进日期到 1601年6月（葛贤抗税）")
        L(f"\n--- Round {i} ---")
        L(f"  input: {inp}")
        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            L(f"  ❌ 失败: {e}")
            continue
        items = list(game.state.discoveries.get("items", {}).values())
        persons = list(game.state.discoveries.get("persons", {}).values())
        places = list(game.state.discoveries.get("places", {}).values())
        facts = game.state.discoveries.get("facts", [])
        n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
        L(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, rice={game.state.rice:.1f}")
        L(f"  discoveries: items={len(items)}, persons={len(persons)}, places={len(places)}, facts={len(facts)}")
        L(f"  financial_log: {len(game.state.financial_log)} 条")
        L(f"  triggered_events: {len(game.state.triggered_events)} 个")
        L(f"  monthly_settle: {n_settle} 次")
        L(f"  current_city: {game.state.current_city}")
        L(f"  current_date: {game.state.current_date}")

    elapsed = time.time() - t0

    # 检查 1601 葛贤抗税
    ge_xian = any("葛贤" in n.get("narrative", "") for n in game.state.narrative_history if isinstance(n, dict))
    L(f"\n=== 1601 葛贤抗税检查 ===")
    L(f"  narrative 含'葛贤': {ge_xian}")
    L(f"  triggered_events: {sorted(game.state.triggered_events)}")

    # Token 报告
    usage = get_usage_logger()
    stats = usage.get_stats()
    L(f"\n=== Token 消耗报告 ===")
    L(f"  总调用: {stats.get('total_calls', 0)}")
    L(f"  总 token: {stats.get('total_tokens', 0)}")
    L(f"  输入 token: {stats.get('total_prompt_tokens', 0)}")
    L(f"  输出 token: {stats.get('total_completion_tokens', 0)}")
    L(f"  错误: {stats.get('error_count', 0)}")
    if stats.get("total_calls", 0) > 0:
        avg = stats.get('total_tokens', 0) / stats['total_calls']
        L(f"  平均/调用: {avg:.0f} token")
    L(f"  耗时: {elapsed:.1f}s")
    L(f"  实时: {stats.get('total_tokens', 0) / elapsed:.0f} token/s")

    # Layer 2 增强验证
    L(f"\n=== Layer 2 增强验证 ===")
    L(f"  items 总数: {len(items)}（应至少 2-3 个）")
    L(f"  persons 总数: {len(persons)}（应至少 1 个）")
    L(f"  places 总数: {len(places)}（应至少 1 个）")
    L(f"  facts 总数: {len(facts)}（应至少 0-1 个）")

    log.close()
    print(f"\n📄 报告写入 logs/test_v1731_10rounds_1601.log")


if __name__ == "__main__":
    main()
