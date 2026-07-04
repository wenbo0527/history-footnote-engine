"""Debug真实LLM的output格式"""
import json, sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager
from history_footnote.dm_agent import DMAgent
from history_footnote.rule_engine import RuleEngine
from history_footnote.game_memory import GameMemory
from history_footnote.knowledge_base import KnowledgeBase
from history_footnote.game_state import make_initial_state
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

config = json.load(open("eras/wanli1587/era.json", "r", encoding="utf-8"))

# 创建一个state
state = make_initial_state("wanli1587", config, "weaving_male")
rule_engine = RuleEngine(config)
memory = GameMemory()
kb = KnowledgeBase(
    entries=config["knowledge"]["entries"],
    snippets=config["knowledge"]["narrative_snippets"],
    story_segments=config["knowledge"].get("story_segments", {}),
)

# 用Minimax
llm = make_llm(provider="minimax-anthropic", era_config=config)
agent = DMAgent(
    era_config=config, state=state, rule_engine=rule_engine,
    memory=memory, knowledge_base=kb, llm_model=llm,
)

# 跑1回合
print("=== 跑真实LLM 1回合 ===")
result = agent.run("我在织机前理经线")

print(f"\nresult keys: {list(result.keys())}")
print(f"\nnarrative长度: {len(result.get('narrative', ''))}")
print(f"\nstate_changes: {result.get('state_changes')}")
print(f"\nupdates: {result.get('updates')}")
print(f"\nevents_to_save: {result.get('events_to_save')}")

print(f"\n=== narrative前500字 ===")
print(result.get('narrative', '')[:500])