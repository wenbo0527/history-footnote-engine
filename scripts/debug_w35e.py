"""W35 monkey patch debug"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

from history_footnote.dm_agent.tools import make_tools as original_make_tools
results = []
def wrapped(*args, **kwargs):
    r = original_make_tools(*args, **kwargs)
    results.append((len(r), [t.name for t in r]))
    return r

import history_footnote.dm_agent.agent as agent_mod
agent_mod.make_tools = wrapped

from history_footnote.dm_agent.agent import DMAgent
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = 'wanli1587'
llm = MagicMock()
llm.bind_tools = MagicMock(return_value=MagicMock())

agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)

print(f'make_tools call count: {len(results)}')
for i, (count, names) in enumerate(results):
    print(f'Call {i}: {count} tools')
    print(f'  Last 2: {names[-2:]}')
print(f'\\nDMAgent.tools ({len(agent.tools)}): {[t.name for t in agent.tools][-2:]}')
