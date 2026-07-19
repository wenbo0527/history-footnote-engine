"""5回合真实Minimax LLM抽样分析

目的：分析Minimax LLM真实生成叙事的质量、格式、风格
- 输出完整narrative
- 检查JSON格式合规性
- 检测是否提到史实关键词
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


SAMPLE_INPUTS = [
    "我在织机前织湖绫",
    "我把织好的湖绫拿到牙行去卖",
    "我去盛泽镇市集看看",
    "我和牙人谈丝价",
    "我听说今年第一批洋船要来了",
]


def main():
    Path("logs").mkdir(exist_ok=True)
    log = open("logs/minimax_5sample.log", "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("Minimax 5回合叙事质量抽样")
    L("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)
    L(f"Provider: Minimax | Model: {config.get('llm', {}).get('model', '?')}")

    save_root = Path("logs/minimax_5sample_save")
    save_root.mkdir(exist_ok=True, parents=True)
    save_manager = SaveManager(save_root)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
        selected_identity="weaving_male",
    )

    captured = io.StringIO()
    old = sys.stdout
    sys.stdout = captured
    try:
        with patch("builtins.input", side_effect=SAMPLE_INPUTS + ["/quit"]):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old

    output = captured.getvalue()
    Path("logs/minimax_5sample_full.txt").write_text(output, encoding="utf-8")

    # 抽取 narrative 块
    import re
    blocks = re.split(r"(?=【[^】]+】|^\[)", output, flags=re.MULTILINE)
    L(f"\n总输出长度: {len(output)}字符")
    L(f"分块数: {len(blocks)}")

    # 查找 narrative 内容
    narr_blocks = []
    for i, b in enumerate(blocks):
        if "叙事" in b[:50] or "narrative" in b[:100].lower():
            narr_blocks.append((i, b[:500]))

    L(f"\n叙事类块数: {len(narr_blocks)}")
    for i, (idx, txt) in enumerate(narr_blocks[:3]):
        L(f"\n--- 叙事块 #{i+1} (block {idx}) ---")
        L(txt)

    # 检测关键词
    keywords = ["织机", "牙行", "盛泽", "湖绫", "丝税", "里长", "里甲", "倭寇", "万历", "苏州", "县衙", "当铺", "高利贷", "逃税", "上供", "蛮族", "党争", "织造"]
    L(f"\n关键词命中:")
    for kw in keywords:
        cnt = output.count(kw)
        if cnt > 0:
            L(f"  {kw}: {cnt}次")

    # 检查 JSON 解析
    from history_footnote.dm_agent import extract_narrative_node  # noqa
    json_blocks = re.findall(r"```json\s*\n(.*?)\n```", output, re.DOTALL)
    L(f"\nLLM 主动输出 JSON 块数: {len(json_blocks)}")
    for jb in json_blocks[:2]:
        try:
            parsed = json.loads(jb)
            L(f"  ✅ JSON可解析: keys={list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__}")
        except Exception as e:
            L(f"  ❌ JSON解析失败: {e}")

    # 最终状态
    L(f"\n最终状态:")
    L(f"  回合: {game.state.round_number}")
    L(f"  日期: {game.state.current_date}")
    L(f"  解锁insight: {sorted(game.state.unlocked_insights)}")
    L(f"  触发事件: {sorted(game.state.triggered_events)}")

    # 加载存档
    auto = save_manager.load_state(game.session, "auto")
    L(f"  存档验证: round={auto.get('round_number')}, events={len(auto.get('events_to_save', []))}")

    log.close()
    print(f"\n[完成] 日志: logs/minimax_5sample.log")
    print(f"[完成] 完整输出: logs/minimax_5sample_full.txt")


if __name__ == "__main__":
    main()
