"""精确 debug DMAgent init 行为"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

from history_footnote.dm_agent.tools import make_tools
from history_footnote.dm_agent.agent import DMAgent
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = 'wanli1587'
llm = MagicMock()
llm.bind_tools = MagicMock(return_value=MagicMock())

# patch make_tools 以 inspect
original_make_tools = make_tools
def patched_make_tools(*args, **kwargs):
    r = original_make_tools(*args, **kwargs)
    print(f'[make_tools called] args[0]=state, era_config={args[4] if len(args) > 4 else "N/A"}')
    print(f'  returns {len(r)} tools, names: {[t.name for t in r]}')
    return r

# monkey patch
import history_footnote.dm_agent.agent as agent_mod
agent_mod.make_tools = patched_make_tools

print('=== Creating DMAgent ===')
agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
print(f'\\n=== After init ===')
print(f'agent.tools count: {len(agent.tools)}')
print(f'agent.tools names: {[t.name for t in agent.tools]}')
print(f'agent.decision_tools count: {len(agent.decision_tools)}')
print(f'agent.decision_tools names: {[t.name for t in agent.decision_tools]}')
