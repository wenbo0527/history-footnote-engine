"""🆕 v1.7.30 真实 LLM 端到端验证（1 轮）

目的：用真实 LLM（minimax-anthropic 或 deepseek）跑 1 轮游戏，
验证 v1.7.30 新功能（evt.* / discover.* / settlement / check_calendar）的端到端工作。

跑 6 轮：
- Round 1-3: 触发 fin.* / discover.* / city.* 事件
- Round 4-6: 累计 6 回合 → 触发月度结算（每 3 回合）
"""
import io
import json
import sys
import tempfile
import unittest.mock as mock
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    from history_footnote.game_loop import GameLoop
    from history_footnote.llm_providers import make_llm
    from history_footnote.storage.save_manager import SaveManager

    print("=" * 60)
    print("v1.7.30 真实 LLM 端到端验证")
    print("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    # 真实 LLM
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        print("✅ LLM: minimax-anthropic")
    except Exception as e:
        print(f"⚠️ minimax-anthropic 不可用: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        print("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_real_"))
    save = SaveManager(tmp)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save,
        selected_identity="weaving_male",
    )
    game.state.cash = 3.0
    game.state.rice = 5.0
    game.state.debt = 1.0
    game.state.monthly_burn = 1.2
    game.state.add_property("shengze", {"id": "p1", "type": "shop", "name": "织房", "value": 15, "rent_per_month": 0.3})
    game.state.add_family_member({"id": "fm_wife", "name": "沈氏", "relation": "wife", "location": "shengze"})

    print(f"\n初始: cash={game.state.cash:.2f}, rice={game.state.rice:.1f}, debt={game.state.debt:.2f}")

    inputs = [
        "我织了一匹湖绫，丝光莹润。",
        "我去镇上牙行卖这匹湖绫。",
        "我搭船去苏州，听说阊门码头很热闹。",
        "在苏州，我找了家茶馆坐坐，听说最近织造局加税了。",
        "我回盛泽，把苏州的见闻告诉沈氏。",
        "我算算家里的账，发现这个月支出很大。",
    ]
    for i, inp in enumerate(inputs, 1):
        print(f"\n--- Round {i} ---")
        print(f"  input: {inp}")
        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            continue
        # 验证
        items = list(game.state.discoveries.get("items", {}).values())
        persons = list(game.state.discoveries.get("persons", {}).values())
        places = list(game.state.discoveries.get("places", {}).values())
        facts = game.state.discoveries.get("facts", [])
        n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
        print(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, rice={game.state.rice:.1f}")
        print(f"  discoveries: items={len(items)}, persons={len(persons)}, places={len(places)}, facts={len(facts)}")
        print(f"  financial_log: {len(game.state.financial_log)} 条")
        print(f"  triggered_events: {sorted(game.state.triggered_events)[:3]}")
        print(f"  monthly_settle 触发: {n_settle} 次")
        print(f"  current_city: {game.state.current_city}")
        print(f"  narrative: {len(game.state.narrative_history)} 条")

    print("\n" + "=" * 60)
    print("✅ 真实 LLM 跑 6 轮完成")
    print("=" * 60)
    return True


if __name__ == "__main__":
    main()
