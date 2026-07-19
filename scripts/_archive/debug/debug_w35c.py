"""Debug W35 make_tools vs DMAgent.tools"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
from history_footnote.dm_agent.tools import make_tools
from history_footnote.dm_agent.agent import DMAgent
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = "wanli1587"

# 1. 直接调 make_tools
tools_a = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
print(f"make_tools() returns: {len(tools_a)}")
names_a = [t.name for t in tools_a]
print(f"  {names_a}")

# 2. 通过 DMAgent
llm = MagicMock()
llm.bind_tools = MagicMock(return_value=MagicMock())
agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
print(f"\nDMAgent.tools: {len(agent.tools)}")
names_b = [t.name for t in agent.tools]
print(f"  {names_b}")

# 3. 差异
print("\nDifferences:")
print(f"  In make_tools but not in agent: {set(names_a) - set(names_b)}")
print(f"  In agent but not in make_tools: {set(names_b) - set(names_a)}")
