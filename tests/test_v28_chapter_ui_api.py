"""v2.8.0 段 UI 章节制 API 测试

测试目标：
1. /api/chapter/state 返回正确格式
2. /api/chapter/blueprint 返回节点数据
3. /api/chapter/history 返回章节历史
4. /api/chapter/record_choice 写入 recent_path_choices
5. 无 session → 400/404 错误

约束：
- 不打真 LLM
- 不影响现有 232 测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_mock_handler(body=None, query=""):
    """构造 mock BaseHTTPRequestHandler（含 _json）"""
    handler = MagicMock()
    handler._json = MagicMock()

    # 把调 _json 时的 (code, data) 记录
    handler.calls = []
    def record(code, data):
        handler.calls.append((code, data))
    handler._json.side_effect = record

    return handler


def make_mock_game():
    """构造模拟 game（含 state + chapter_state）"""
    from history_footnote.game_state import GameState

    game = MagicMock()
    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 8
    state.player_build = "外望人"
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.chapter_state.last_closure_status = "CONTINUE"
    state.chapter_state.blueprint = {
        "chapter_id": 1,
        "chapter_title": "且听下回分解 · 春蚕",
        "chapter_subtitle": "春风又绿江南岸",
        "transition_hint": "season",
        "meta": {
            "act": "departure",
            "role": "ordinary",
            "emotion_tone": "unease→resolve",
            "suggested_node_count": 4,
        },
        "nodes": [
            {"index": 1, "role": "introduction", "scene": "scene 1", "npc_ids": ["fm_wife"]},
            {"index": 2, "role": "escalation", "scene": "scene 2", "npc_ids": ["npc_zhao_lizhang"]},
            {"index": 3, "role": "climax", "scene": "scene 3", "npc_ids": ["npc_zhao_lizhang"]},
            {"index": 4, "role": "resolution", "scene": "scene 4", "npc_ids": ["fm_wife"]},
        ],
    }
    state.path_state.main_path_focus = "main_tax_resistance"
    state.path_state.active_paths = ["main_tax_resistance"]
    state.plate_state.statuses = {"central_plains": "stable", "northwest": "tense"}
    state.chapter_state.chapter_history = []
    state.recent_path_choices = []

    game.state = state
    game.era_config = {}
    game.session_id = "test-session-1"

    return game


# Mock _get_or_load_session
import history_footnote.web_server.routers.chapter as chapter_router
from unittest.mock import patch


def setup_mock_session(game):
    """patch session lookup 返回指定 game"""
    return patch.object(
        chapter_router, '_get_or_load_session', return_value=game
    )


# ============= 测试 1：/api/chapter/state =============

def test_V28_195_api_chapter_state_returns_chapter_progress():
    """GET /api/chapter/state 返回章节进度"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_state
    game = make_mock_game()
    handler = make_mock_handler()

    with setup_mock_session(game):
        # patch 同时覆盖 _get_game_or_404 间接用到的 _get_or_load_session
        result = handle_GET_chapter_state(handler, query="session_id=test-session-1")

    assert result is True
    assert len(handler.calls) == 1, f"期望 1 次 _json 调用，实际 {len(handler.calls)}"
    code, data = handler.calls[0]
    assert code == 200
    assert data["active"] is True
    assert data["current_chapter"] == 1
    assert data["current_node"] == 2
    assert data["node_count"] == 4
    # 当前节点 2/4 → 50%
    assert abs(data["progress_pct"] - 50.0) < 0.1
    assert data["round_number"] == 8
    return True


def test_V28_196_api_chapter_state_missing_session():
    """缺 session_id 返回 400"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_state
    handler = make_mock_handler()

    result = handle_GET_chapter_state(handler, query="")

    assert result is True
    code, data = handler.calls[0]
    assert code == 400, f"期望 400，实际 {code}"
    return True


# ============= 测试 2：/api/chapter/blueprint =============

def test_V28_197_api_chapter_blueprint_returns_nodes():
    """GET /api/chapter/blueprint 返回节点数据"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_blueprint
    game = make_mock_game()
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_chapter_blueprint(
            handler, query="session_id=test-session-1"
        )

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["active"] is True
    assert data["chapter_title"] == "且听下回分解 · 春蚕"
    assert len(data["nodes"]) == 4
    assert data["nodes"][0]["role"] == "introduction"
    assert data["meta"]["act"] == "departure"
    return True


def test_V28_198_api_chapter_blueprint_inactive_returns_empty():
    """无蓝图时返回 active=False（容错）"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_blueprint
    game = make_mock_game()
    game.state.chapter_state.blueprint = None  # 触发兜底
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_chapter_blueprint(
            handler, query="session_id=test-session-1"
        )

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["active"] is False
    return True


# ============= 测试 3：/api/chapter/history =============

def test_V28_199_api_chapter_history_returns_settled_chapters():
    """GET /api/chapter/history 返回章节历史"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_history
    game = make_mock_game()
    # 加 1 章历史
    game.state.chapter_state.chapter_history = [
        {
            "chapter": 1,
            "summary": "暮色渐沉，玩家签下欠据",
            "core_event": "玩家签下欠据",
            "key_choice": "签下欠据",
            "build_summary": "尽责偏正+0.8",
            "path_summary": "main_tax_resistance",
            "rounds_in_chapter": 16,
            "ended_at_round": 16,
            "transition": "season",
            "closure_status": "SOFT_READY",
        },
    ]
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_chapter_history(
            handler, query="session_id=test-session-1"
        )

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["count"] == 1
    assert data["history"][0]["chapter"] == 1
    assert "暮色渐沉" in data["history"][0]["summary"]
    assert data["history"][0]["closure_status"] == "SOFT_READY"
    return True


# ============= 测试 4：/api/chapter/record_choice =============

def test_V28_200_api_chapter_record_choice_writes_path():
    """POST /api/chapter/record_choice 写入 recent_path_choices"""
    from history_footnote.web_server.routers.chapter import handle_POST_record_choice
    game = make_mock_game()
    handler = make_mock_handler()
    body = {
        "session_id": "test-session-1",
        "path": "main_tax_resistance",
    }

    with setup_mock_session(game):
        result = handle_POST_record_choice(handler, body=body)

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["recorded"] is True
    assert data["path"] == "main_tax_resistance"
    assert "main_tax_resistance" in data["recent_path_choices"]
    # state.recent_path_choices 也应被写入
    assert "main_tax_resistance" in game.state.recent_path_choices
    return True


# ============= 测试 5：/api/chapter/state 无章节（老存档） =============

def test_V28_201_api_chapter_state_for_old_save_returns_inactive():
    """老存档无 chapter_state → 返回 active=False（零回归）"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_state
    from history_footnote.game_state import GameState

    game = MagicMock()
    state = GameState()
    state.era_id = "wanli1587"
    # 没有 chapter_state（模拟老存档）
    state.chapter_state = None
    state.round_number = 3
    state.path_state.main_path_focus = ""
    state.plate_state.statuses = {}
    game.state = state
    game.era_config = {}
    game.session_id = "old-save-1"

    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_chapter_state(handler, query="session_id=old-save-1")

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["active"] is False  # 老存档不显示进度条
    assert data["current_chapter"] == 0
    return True


def test_V28_202_api_chapter_state_with_active_plate():
    """state 含 shifting 板块 → 返回 active_plate"""
    from history_footnote.web_server.routers.chapter import handle_GET_chapter_state
    game = make_mock_game()
    game.state.plate_state.statuses = {
        "central_plains": "stable",
        "jiangnan": "shifting",  # shifting 状态
    }
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_chapter_state(handler, query="session_id=test-session-1")

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["active_plate"] == "jiangnan"
    return True
