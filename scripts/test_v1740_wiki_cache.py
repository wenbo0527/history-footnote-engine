"""🆕 v1.7.40 真实 LLM 跑 5 轮（验证 Wiki cache 长期命中率）"""
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

    log_path = Path("logs/test_v1740_wiki_cache.log")
    log = open(log_path, "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("v1.7.40 真实 LLM 跑 5 轮（Wiki cache 长期数据）")
    L("=" * 60)

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    try:
        llm = make_llm(provider="minimax-anthropic", era_config=config)
        L("✅ LLM: minimax-anthropic")
    except Exception as e:
        L(f"⚠️ minimax-anthropic 失败: {e}")
        llm = make_llm(provider="deepseek", era_config=config)
        L("✅ LLM: deepseek")

    tmp = Path(tempfile.mkdtemp(prefix="hf_v1740_"))
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
    game.state.add_family_member({"id": "fm_wife", "name": "沈氏", "relation": "wife", "location": "shengze"})

    # 5 轮：focus 在 苏州/songjiang 城市（让 cache 命中）
    inputs = [
        "我搭船去苏州阊门码头。",
        "我回家告诉沈氏这事。",
        "我又搭船去苏州听人聊行情。",
        "我又回家。",
        "我回苏州。",
    ]

    cache_snapshots = []
    t0 = time.time()
    for i, inp in enumerate(inputs, 1):
        L(f"\n--- Round {i}: {inp} ---")
        try:
            with redirect_stdout(io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            L(f"  ❌ 失败: {e}")
            continue
        # 用 facade.get_performance_stats() 拿 cache 命中
        perf = game.engine.get_performance_stats()
        cache_stats = perf["wiki_cache"]
        snapshot = {
            "round": i,
            "cache_size": cache_stats["cache_size"],
            "hit_rate": cache_stats["hit_rate"],
        }
        cache_snapshots.append(snapshot)
        L(f"  city={game.state.current_city}, cash={game.state.cash:.2f}")
        L(f"  Wiki cache: size={snapshot['cache_size']}, hit_rate={snapshot['hit_rate']:.0%}")
    elapsed = time.time() - t0

    L(f"\n{'='*60}")
    L(f"📊 Wiki cache 长期数据")
    L(f"{'='*60}")
    for s in cache_snapshots:
        L(f"  Round {s['round']}: size={s['cache_size']}, hit={s['hit_rate']:.0%}")
    final_cache = game.engine.get_wiki_cache_stats()
    L(f"\n最终:")
    L(f"  cache_size: {final_cache['cache_size']}")
    L(f"  cache_max: {final_cache['cache_max']}")
    L(f"  hit_rate: {final_cache['hit_rate']:.0%}")
    L(f"  耗时: {elapsed:.1f}s")

    log.close()
    print(f"\n📄 报告写入 {log_path}")


if __name__ == "__main__":
    main()
