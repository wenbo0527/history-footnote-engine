"""Debug V32_007"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/tests')
from history_footnote.chapter.dm_tool import build_chapter_tool_prompt
from history_footnote.game_state import GameState
state = GameState()
state.era_id = "wanli1587"
era_config = {
    "narrative": {
        "hero_journey_acts": [
            {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
        ],
    },
}
prompt = build_chapter_tool_prompt(state, 1, era_config)
print("=== Prompt 全文 ===")
print(prompt)
print("=== END ===")
print("W32 硬约束" in prompt, "W33 硬约束" in prompt)
