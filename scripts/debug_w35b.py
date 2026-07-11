"""Debug W35 决策类"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
from history_footnote.dm_agent.agent import DMAgent
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = "wanli1587"
llm = MagicMock()
llm.bind_tools = MagicMock(return_value=MagicMock())

agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
print(f"Total tools: {len(agent.tools)}")
print(f"Decision tools: {len(agent.decision_tools)}")
for t in agent.decision_tools:
    print(f"  decision: {t.name}")
print(f"Query tools: {len(agent.query_tools)}")
for t in agent.query_tools:
    print(f"  query: {t.name}")
print()
print(f"bind_tools called: {llm.bind_tools.called}")
if llm.bind_tools.called:
    call_args = llm.bind_tools.call_args
    print(f"args len: {len(call_args[0])}")
    if call_args[0]:
        print(f"first arg type: {type(call_args[0][0])}")
        print(f"first arg len: {len(call_args[0][0])}")
