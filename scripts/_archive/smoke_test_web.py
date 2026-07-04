"""Web server smoke test - 用 Mock LLM"""
import sys, json, threading
sys.path.insert(0, "src")
import history_footnote.web_server as ws
from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop

config = json.loads(open("eras/wanli1587/era.json").read())
llm = MockDMChatModel(era_config=config)
game = GameLoop(era_id="wanli1587", era_config=config, llm_model=llm, selected_identity="weaving_male")
ws._SESSIONS[game.session.session_id] = (game, threading.Lock())
sid = game.session.session_id
print(f"Created session: {sid}")
print(f"Round: {game.state.round_number}, date: {game.state.current_date}")
print(f"Insights: {sorted(game.state.unlocked_insights)}")

# 跑一回合
state = ws._format_state(game)
print(f"\nFormat state keys: {list(state.keys())}")
print(f"Recent narratives: {len(state['recent_narratives'])}")

# 跑一回合
game._preprocess_input("我去集市上看看")
game._run_round("我去集市上看看")
print(f"\nAfter 1 round: {game.state.round_number}")
print(f"Insights: {sorted(game.state.unlocked_insights)}")
print(f"Last narrative: {game.state.narrative_history[-1]['narrative'][:100]}...")
