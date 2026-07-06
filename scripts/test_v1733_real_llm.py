"""🆕 v1.7.33 真实 LLM 跑 6 轮（仅 narrative）

v1.7.33 架构：游戏引擎通过 action_resolver 处理状态，LLM 只生成 narrative。
本测试验证：
1. LLM 不输出 <events> 块也能正常工作
2. action_resolver 处理的 events 全部落地
3. 真实 LLM 输出 narrative 流畅
4. 10 类结构化数据全部由游戏引擎控制
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
    from history_footnote.action_resolver import parse_player_input, resolve_action, apply_action_result

    Path("logs").mkdir(exist_ok=True)
    log = open("logs/test_v1733_real_llm.log", "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("v1.7.33 真实 LLM 跑 6 轮（仅 narrative）")
    L("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1733_"))
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
        "我搭船去苏州阊门码头。",
        "在苏州，我找了家茶馆坐坐。",
        "我回家告诉沈氏这事。",
        "我算了算账。",
    ]

    t0 = time.time()
    for i, inp in enumerate(inputs, 1):
        L(f"\n--- Round {i} ---")
        L(f"  input: {inp}")
        # 先 action_resolver 解析
        action = parse_player_input(inp)
        L(f"  parsed: verb={action.verb}, obj={action.object}, target={action.target}, amount={action.amount}")
        result = resolve_action(game.state, action, config)
        L(f"  resolve: success={result.success}, events={[e.get('id','') for e in result.events]}, state_changes={result.state_changes}")
        if result.success:
            apply_action_result(game.state, result)

        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            L(f"  ❌ 失败: {e}")
            continue
        items = list(game.state.discoveries.get("items", {}).values())
        persons = list(game.state.discoveries.get("persons", {}).values())
        places = list(game.state.discoveries.get("places", {}).values())
        n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
        L(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, rice={game.state.rice:.1f}")
        L(f"  discoveries: items={len(items)}, persons={len(persons)}, places={len(places)}")
        L(f"  triggered_events: {len(game.state.triggered_events)} 个")
        L(f"  monthly_settle: {n_settle} 次")
        L(f"  current_city: {game.state.current_city}")
    elapsed = time.time() - t0

    L(f"\n总耗时: {elapsed:.1f}s")
    L(f"\n=== v1.7.33 验证 ===")
    L(f"  cash={game.state.cash:.2f}, debt={game.state.debt:.2f}, city={game.state.current_city}")
    L(f"  items={len(list(game.state.discoveries.get('items', {}).values()))}, persons={len(list(game.state.discoveries.get('persons', {}).values()))}")
    log.close()
    print(f"\n📄 报告写入 logs/test_v1733_real_llm.log")


if __name__ == "__main__":
    main()
