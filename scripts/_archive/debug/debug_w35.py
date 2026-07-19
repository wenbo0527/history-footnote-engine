"""Debug W35 1"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
from history_footnote.dm_agent.tools import make_tools
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = "wanli1587"
tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
print(f"Tools count: {len(tools)}")
for t in tools:
    print(f"  {t.name}: {t.description[:60] if t.description else 'NO DESC'}")
