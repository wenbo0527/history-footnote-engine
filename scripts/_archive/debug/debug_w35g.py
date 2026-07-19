"""Test make_tools 12 个 + agent.tools 10 个差异"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

# 1. 独立调 make_tools
from history_footnote.dm_agent.tools import make_tools
from history_footnote.game_state import GameState
from unittest.mock import MagicMock

state = GameState()
state.era_id = 'wanli1587'
t1 = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
print(f'1. make_tools: {len(t1)}')
print(f'   {[t.name for t in t1]}')

# 2. 第二次调
t2 = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
print(f'2. make_tools again: {len(t2)}')

# 3. 多次
for i in range(3):
    t = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
    print(f'3.{i}: {len(t)}')

# 4. 长时间不变吗
import time
time.sleep(1)
t = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
print(f'4: {len(t)}')

# 5. 再用 spec=RuleEngine
from history_footnote.rule_engine import RuleEngine
from history_footnote.game_memory import GameMemory
from history_footnote.knowledge_base import KnowledgeBase
t = make_tools(state, MagicMock(spec=RuleEngine), MagicMock(spec=GameMemory), MagicMock(spec=KnowledgeBase), {})
print(f'5. with spec: {len(t)}')
