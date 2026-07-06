"""🆕 v1.7.37 真实 LLM 跑 1 轮（验证 Wiki 注入）"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    from history_footnote.game_loop import GameLoop
    from history_footnote.llm_providers import make_llm
    from history_footnote.storage.save_manager import SaveManager

    log_path = Path("logs/test_v1737_real_llm_1round.log")
    log = open(log_path, "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("v1.7.37 真实 LLM 跑 1 轮（验证 Wiki 注入）")
    L("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1737_"))
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
    game.state.add_property("shengze", {"id": "p1", "type": "shop", "name": "织房", "value": 15, "rent_per_month": 0.3})

    # 跑 1 轮：去苏州
    L("\n--- Round 1: 搭船去苏州 ---")
    try:
        with redirect_stdout(io.StringIO()):
            game._run_round("我搭船去苏州")
    except Exception as e:
        L(f"❌ 失败: {e}")

    # 验证 Wiki 注入
    L(f"\n=== Wiki 注入验证 ===")
    # 检查 state_ref 中是否有 wiki_hint
    if hasattr(game.dm.llm, "_state_ref_slot_ref"):
        state_ref = game.dm.llm._state_ref_slot_ref[0]
        wiki_hint = state_ref.get("wiki_hint", "")
        L(f"  state_ref.wiki_hint 长度: {len(wiki_hint)} 字符")
        if wiki_hint:
            L(f"  内容预览:")
            for line in wiki_hint.split("\n")[:10]:
                L(f"    {line}")
        else:
            L(f"  ⚠️ wiki_hint 为空（未注入）")

    # 检查 narrative
    L(f"\n=== Narrative 历史 ===")
    L(f"  narrative_history: {len(game.state.narrative_history)} 条")
    for n in game.state.narrative_history[:3]:
        if isinstance(n, dict):
            L(f"    [{n.get('type', '')}] {n.get('narrative', '')[:100]}...")
        else:
            L(f"    {str(n)[:100]}...")

    L(f"\n=== 当前状态 ===")
    L(f"  cash: {game.state.cash:.2f}, city: {game.state.current_city}")
    items = list(game.state.discoveries.get("items", {}).values())
    L(f"  discoveries.items: {len(items)}")
    places = list(game.state.discoveries.get("places", {}).values())
    L(f"  discoveries.places: {len(places)}")
    for p in places[:3]:
        L(f"    - {p.get('name', '')}")

    log.close()
    print(f"\n📄 报告写入 {log_path}")


if __name__ == "__main__":
    main()
