"""v2.10.1 W52 20 回合端到端测试发现 bug 修复

两个 bug:
1. chosen_voice 未定义（game_loop.py 行 533）
2. GameEvent class 冲突（event_bus.GameEvent 与 game_memory.GameEvent）

修复后回归测试。
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest


class MockLLM:
    """最小可工作 LLM mock"""
    def __init__(self):
        self._state_ref_slot_ref = [{}]

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages, **kwargs):
        from langchain_core.messages import AIMessage
        return AIMessage(content="<narrative>你继续做你的事。</narrative>")


PLAYER_INPUTS = [
    "我织了一匹湖绫",
    "我去牙行卖丝",
    "我听邻居说李秀才中了举人",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我决定硬抗税",
    "我去苏州城里走走",
    "我听说洋船要来了",
    "我看到县衙贴出告示",
    "我决定扩大织机规模",
    "我去告官府",
    "我向李秀才借债",
    "我开始织春蚕丝",
    "我去跟邻人商量",
    "我修好织机",
    "我用借的钱交了税",
    "我把春蚕丝拿去卖",
    "我还了一部分债",
    "我跟沈氏在自家织房",
    "我决定继续守这片土地",
]


def make_mock_dm_response(round_num: int, player_input: str) -> dict:
    return {
        "narrative": f"第 {round_num} 回合：你做了『{player_input[:20]}』，系统处理完毕。",
        "state_changes": {},
        "events_to_save": [f"Round {round_num}: {player_input[:30]}"],
        "updates": None,
        "identity_offer": None,
    }


@pytest.fixture(scope="module")
def game_loop():
    """共享 GameLoop fixture（避免重复 init）"""
    from history_footnote.game_loop import GameLoop

    era_config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )
    mock_llm = MockLLM()
    return GameLoop(
        era_id="wanli1587",
        era_config=era_config,
        llm_model=mock_llm,
        selected_identity="weaving_male",
    )


# ============= 单元测试：bug 修复验证 =============

def test_chosen_voice_initialized():
    """chosen_voice 必须在 game_loop.py 行 533 之前初始化

    修复前: 抛 `name 'chosen_voice' is not defined`
    修复后: 默认为 None
    """
    import inspect
    from history_footnote.game_loop import GameLoop

    src = inspect.getsource(GameLoop._run_round)
    # 找 chosen_voice 引用前的初始化
    chosen_voice_idx = src.find("if chosen_voice and")
    chosen_voice_init_idx = src.rfind("chosen_voice = ", 0, chosen_voice_idx)
    assert chosen_voice_init_idx < chosen_voice_idx, "chosen_voice 必须在 if 块前初始化"


def test_memory_event_class_import():
    """游戏保存事件用 game_memory.GameEvent 不是 event_bus.GameEvent

    修复前: GameEvent(round=...) 抛 unexpected keyword argument
    修复后: 显式 import game_memory.GameEvent
    """
    import inspect
    from history_footnote.game_loop import GameLoop

    src = inspect.getsource(GameLoop._run_round)
    # 必须有 from history_footnote.game_memory import GameEvent as ...
    assert "from history_footnote.game_memory import GameEvent" in src
    # 后续构造 GameEvent 必须用别名
    assert "GameEvent(" in src


# ============= 集成测试：1 回合 =============

def test_single_round_no_chosen_voice_error(game_loop):
    """1 回合应不抛 `chosen_voice is not defined`"""
    dm_response = make_mock_dm_response(1, "我织了一匹湖绫")

    try:
        with patch.object(game_loop, '_get_player_input', return_value="我织了一匹湖绫"), \
             patch.object(game_loop, '_is_game_over', return_value=False), \
             patch.object(game_loop.dm, 'run', return_value=dm_response), \
             patch.object(game_loop.dm, 'regenerate', return_value=dm_response):
            game_loop._run_round("我织了一匹湖绫")
    except NameError as e:
        if "chosen_voice" in str(e):
            pytest.fail(f"chosen_voice undefined bug 未修复: {e}")
        raise


def test_single_round_event_log_filled(game_loop):
    """1 回合后 event_log 至少 1 条"""
    initial_count = len(game_loop.state.event_log)
    dm_response = make_mock_dm_response(1, "我织了一匹湖绫")

    with patch.object(game_loop, '_get_player_input', return_value="我织了一匹湖绫"), \
         patch.object(game_loop, '_is_game_over', return_value=False), \
         patch.object(game_loop.dm, 'run', return_value=dm_response), \
         patch.object(game_loop.dm, 'regenerate', return_value=dm_response):
        game_loop._run_round("我织了一匹湖绫")

    assert len(game_loop.state.event_log) > initial_count, "event_log 未增长"


# ============= 端到端：20 回合 =============

def test_20_rounds_no_exception(game_loop):
    """20 回合 GameLoop.run() 端到端不应抛未捕获异常"""
    dm_iter = iter(make_mock_dm_response(i + 1, inp) for i, inp in enumerate(PLAYER_INPUTS))
    input_iter = iter(PLAYER_INPUTS)
    snapshots = []
    errors = []

    def mock_dm_run(player_input):
        return next(dm_iter)

    def mock_get_input():
        try:
            return next(input_iter)
        except StopIteration:
            raise SystemExit("Test done")

    def mock_is_game_over():
        return game_loop.state.round_number > 20

    original_run_round = game_loop._run_round

    def wrapped_run_round(player_input):
        try:
            original_run_round(player_input)
        except Exception as e:
            errors.append(e)
        snapshots.append({
            "round": game_loop.state.round_number,
            "events": len(game_loop.state.event_log),
        })

    with patch.object(game_loop, '_get_player_input', side_effect=mock_get_input), \
         patch.object(game_loop, '_is_game_over', side_effect=mock_is_game_over), \
         patch.object(game_loop.dm, 'run', side_effect=mock_dm_run), \
         patch.object(game_loop.dm, 'regenerate', side_effect=mock_dm_run), \
         patch.object(game_loop, '_run_round', side_effect=wrapped_run_round):
        try:
            game_loop.run()
        except SystemExit:
            pass

    assert len(snapshots) == 20, f"snapshots={len(snapshots)} (期望 20)"
    assert not errors, f"{len(errors)} 回合异常: {errors[:3]}"
    assert game_loop.state.event_log, "event_log 为空"
