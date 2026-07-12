"""手测 1 回合找 extract_narrative_node 位置"""
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 构造真 LLM
from history_footnote.llm_wrapper import get_wrapped_llm
real_llm = get_wrapped_llm(primary_provider="minimax-anthropic")

from history_footnote.game_loop import GameLoop
era_config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

loop = GameLoop(
    era_id="wanli1587",
    era_config=era_config,
    llm_model=real_llm,
    selected_identity="weaving_male",
)

try:
    loop._run_round("我织了一匹湖绫")
    print(f"OK round={loop.state.round_number}")
    print(f"event_log: {len(loop.state.event_log)}")
    nh = getattr(loop.state, "narrative_history", [])
    print(f"narrative_history: {len(nh)}")
    if nh:
        for i, n in enumerate(nh[-3:], 1):
            print(f"  [{i}] type={type(n).__name__} keys={list(n.keys()) if isinstance(n, dict) else '?'}")
            if isinstance(n, dict):
                summary = n.get("summary", "")
                print(f"      summary: {summary[:80]}...")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
