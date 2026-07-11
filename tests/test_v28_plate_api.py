"""v2.8.x W28 板块格局 API 测试

测试目标：
1. GET /api/chapter/plate 格式
2. 无 session → 400
3. 老存档（无 plate_state）→ 200 + 全 0 / stable
4. plate_state 含 shifting → active_plate 字段返回
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_mock_handler():
    handler = MagicMock()
    handler._json = MagicMock()
    handler.calls = []
    def record(code, data):
        handler.calls.append((code, data))
    handler._json.side_effect = record
    return handler


def make_mock_game(era_config=None, plate_state=None):
    from history_footnote.game_state import GameState
    game = MagicMock()
    state = GameState()
    state.era_id = "wanli1587"
    state.plate_state = plate_state
    game.state = state
    game.era_config = era_config or {}
    game.session_id = "test-plate-1"
    return game


# Mock _get_or_load_session
import history_footnote.web_server.routers.chapter as chapter_router


def setup_mock_session(game):
    return patch.object(
        chapter_router, '_get_or_load_session', return_value=game
    )


# ============= 测试 1：/api/chapter/plate 基础 =============

def test_V28_203_api_plate_returns_definitions():
    """GET /api/chapter/plate 返回板块定义"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map

    era_config = {
        "plates": {
            "plate_definitions": [
                {"id": "central_plains", "name": "中原", "type": "core", "neighbors": ["jiangnan"], "base_tension": 0.3, "description": "中原"},
                {"id": "jiangnan", "name": "江南", "type": "core", "neighbors": ["central_plains"], "base_tension": 0.4, "description": "江南"},
            ],
            "corridors": [
                {"id": "grand_canal", "from_plate": "central_plains", "to_plate": "jiangnan", "description": "大运河"},
            ],
        }
    }
    game = make_mock_game(era_config=era_config)
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_plate_map(handler, query="session_id=test-plate-1")

    assert result is True
    code, data = handler.calls[0]
    assert code == 200
    assert data["active"] is True
    assert data["plate_count"] == 2
    assert len(data["definitions"]) == 2
    # 第一块是 central_plains
    assert data["definitions"][0]["id"] == "central_plains"
    # 走廊
    assert len(data["corridors"]) == 1
    assert data["corridors"][0]["id"] == "grand_canal"
    return True


def test_V28_204_api_plate_missing_session():
    """缺 session_id → 400"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map
    handler = make_mock_handler()
    result = handle_GET_plate_map(handler, query="")
    code, data = handler.calls[0]
    assert code == 400
    return True


# ============= 测试 2：老存档 =============

def test_V28_205_api_plate_old_save_no_plate_state():
    """老存档（无 plate_state）→ 200 + 全 stable / 0 tension"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map

    era_config = {
        "plates": {
            "plate_definitions": [
                {"id": "p1", "name": "P1", "type": "core", "neighbors": [], "base_tension": 0.5, "description": "d"},
            ],
        }
    }
    game = make_mock_game(era_config=era_config, plate_state=None)
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_plate_map(handler, query="session_id=test-plate-1")

    code, data = handler.calls[0]
    assert code == 200
    assert data["tensions"]["p1"] == 0.0
    assert data["statuses"]["p1"] == "stable"
    return True


# ============= 测试 3：shifting 激活 =============

def test_V28_206_api_plate_shifting_returns_active():
    """plate_state 含 shifting → active_plate 字段返回"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map

    era_config = {
        "plates": {
            "plate_definitions": [
                {"id": "central_plains", "name": "中原", "type": "core", "neighbors": [], "base_tension": 0.3, "description": "d"},
                {"id": "jiangnan", "name": "江南", "type": "core", "neighbors": [], "base_tension": 0.4, "description": "d"},
            ],
        }
    }
    # 模拟 plate_state: jiangnan 是 shifting
    plate_state = MagicMock()
    plate_state.statuses = {"central_plains": "stable", "jiangnan": "shifting"}
    plate_state.get_tension.side_effect = lambda pid: 0.8 if pid == "jiangnan" else 0.3

    game = make_mock_game(era_config=era_config, plate_state=plate_state)
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_plate_map(handler, query="session_id=test-plate-1")

    code, data = handler.calls[0]
    assert code == 200
    assert data["active_plate"] == "jiangnan"
    assert data["statuses"]["jiangnan"] == "shifting"
    assert data["tensions"]["jiangnan"] == 0.8
    return True


# ============= 测试 4：边界 =============

def test_V28_207_api_plate_empty_era_config():
    """空 era_config（无 plates 字段）→ 0 plates 不崩"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map

    game = make_mock_game(era_config={})
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_plate_map(handler, query="session_id=test-plate-1")

    code, data = handler.calls[0]
    assert code == 200
    assert data["plate_count"] == 0
    assert data["definitions"] == []
    return True


def test_V28_208_api_plate_corridors_without_plates():
    """有 corridors 但无 plates → 不应崩"""
    from history_footnote.web_server.routers.chapter import handle_GET_plate_map

    era_config = {
        "plates": {
            "plate_definitions": [],
            "corridors": [{"id": "c1", "from_plate": "a", "to_plate": "b", "description": "d"}],
        }
    }
    game = make_mock_game(era_config=era_config)
    handler = make_mock_handler()

    with setup_mock_session(game):
        result = handle_GET_plate_map(handler, query="session_id=test-plate-1")

    code, data = handler.calls[0]
    assert code == 200
    assert data["plate_count"] == 0
    # 走廊独立保留
    assert len(data["corridors"]) == 1
    return True
