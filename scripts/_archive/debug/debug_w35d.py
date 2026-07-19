"""Debug W35 duplicate check"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
from history_footnote.dm_agent.tools import make_tools
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = "wanli1587"
tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})

# 12 个 tool，unique name?
names = [t.name for t in tools]
print(f"Total: {len(tools)}")
print(f"Unique names: {len(set(names))}")
print(f"All names: {names}")
# 用 id 找 duplicates
ids = [id(t) for t in tools]
print(f"Unique ids: {len(set(ids))}")
# 找 duplicate
from collections import Counter
counter = Counter(names)
duplicates = [n for n, c in counter.items() if c > 1]
print(f"Duplicate names: {duplicates}")
