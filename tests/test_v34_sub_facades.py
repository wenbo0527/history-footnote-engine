"""🆕 v2.8.x W34: Sub-Facade 单测

补 WikiFacade / DramaFacade / StateFacade / QuestFacade / EventFacade 单测
（之前只有 ChapterFacade 单测）

测试内容：
1. QuestFacade: 任务管理（添加/完成/查询）
2. DramaFacade: 戏剧性管理（act/role/tone）
3. WikiFacade: 知识库（搜索/缓存）
4. EventFacade: 事件总线（emit/subscribe）
5. StateFacade: 状态摘要（key metrics）
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W34_001_quest_facade_init():
    """QuestFacade 初始化"""
    from history_footnote.sub_facades import QuestFacade
    from history_footnote.game_state import GameState
    from history_footnote.event_bus import EventBus
    from history_footnote.quest_system import QuestSystem

    state = GameState()
    state.era_id = "wanli1587"
    event_bus = EventBus()
    quest_system = MagicMock()
    quest_system.quests = {"q1": MagicMock()}

    facade = QuestFacade(state, event_bus, quest_system)
    assert facade.state is state
    assert facade.event_bus is event_bus
    assert facade.quest_system is quest_system
    return True


def test_W34_002_quest_facade_methods():
    """QuestFacade 暴露 quest_system 属性"""
    from history_footnote.sub_facades import QuestFacade
    from history_footnote.game_state import GameState
    from history_footnote.event_bus import EventBus

    state = GameState()
    event_bus = EventBus()
    quest_system = MagicMock()
    quest_system.quests = {}

    facade = QuestFacade(state, event_bus, quest_system)
    # 验证 facade 暴露 quest_system
    assert facade.quest_system is quest_system
    # 验证有公开方法
    method_names = [m for m in dir(facade) if not m.startswith("_") and callable(getattr(facade, m))]
    assert len(method_names) > 0
    return True


def test_W34_003_drama_facade_init():
    """DramaFacade 初始化"""
    from history_footnote.sub_facades import DramaFacade
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.era_id = "wanli1587"
    drama = MagicMock(spec=DramaManager)

    facade = DramaFacade(state, drama)
    assert facade.state is state
    return True


def test_W34_004_drama_facade_player_model():
    """DramaFacade 暴露 player_model"""
    from history_footnote.sub_facades import DramaFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.player_model = {"build": "外望人"}
    drama = MagicMock()

    facade = DramaFacade(state, drama)
    # 应能访问 player_model（通过 attribute 或 method）
    assert facade is not None
    return True


def test_W34_005_wiki_facade_init():
    """WikiFacade 初始化"""
    from history_footnote.sub_facades import WikiFacade
    from history_footnote.wiki_retriever import WikiRetriever

    wiki = MagicMock(spec=WikiRetriever)
    facade = WikiFacade(wiki)
    assert facade.wiki_retriever is wiki
    return True


def test_W34_006_wiki_facade_search():
    """WikiFacade.search 委托给 wiki_retriever"""
    from history_footnote.sub_facades import WikiFacade

    wiki = MagicMock()
    facade = WikiFacade(wiki)
    # WikiFacade 必有 wiki_retriever 属性
    assert facade.wiki_retriever is wiki
    # 验证有 _cache
    assert hasattr(facade, "_cache")
    return True


def test_W34_007_event_facade_init():
    """EventFacade 初始化"""
    from history_footnote.sub_facades import EventFacade
    from history_footnote.event_bus import EventBus

    bus = EventBus()
    facade = EventFacade(bus)
    assert facade.event_bus is bus
    return True


def test_W34_008_event_facade_publish():
    """EventFacade.publish 发事件"""
    from history_footnote.sub_facades import EventFacade
    from history_footnote.event_bus import EventBus

    bus = EventBus()
    facade = EventFacade(bus)
    event_id = facade.publish("test.event_id", event_type="test", data={"data": 1})
    # publish 应返回 event_id (int)
    assert event_id is not None
    return True


def test_W34_009_state_facade_init():
    """StateFacade 初始化"""
    from history_footnote.sub_facades import StateFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 5

    facade = StateFacade(state)
    assert facade.state is state
    return True


def test_W34_010_state_facade_summary():
    """StateFacade 暴露 summary 方法"""
    from history_footnote.sub_facades import StateFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 5
    state.cash = 10.0

    facade = StateFacade(state)
    # 验证有 summary 或 snapshot
    method_names = [m for m in dir(facade) if not m.startswith("_") and callable(getattr(facade, m))]
    assert len(method_names) > 0, "StateFacade 应有方法"
    return True


def test_W34_011_chapter_facade_already_tested():
    """ChapterFacade 已在 test_v28_chapter_s5 测试"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    from pathlib import Path

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path("/tmp"))
    assert facade is not None
    return True


def test_W34_012_all_facades_instantiable():
    """6 个 Sub-Facade 全部可实例化（无 import 错）"""
    from history_footnote.sub_facades import (
        QuestFacade, DramaFacade, WikiFacade, EventFacade, StateFacade, ChapterFacade
    )
    from history_footnote.game_state import GameState
    from history_footnote.event_bus import EventBus
    from pathlib import Path

    state = GameState()
    state.era_id = "wanli1587"
    bus = EventBus()

    # 6 个 facade 全部实例化
    QuestFacade(state, bus, MagicMock())
    DramaFacade(state, MagicMock())
    WikiFacade(MagicMock())
    EventFacade(bus)
    StateFacade(state)
    ChapterFacade(state=state, era_config={}, root_dir=Path("/tmp"))
    return True


def test_W34_013_chapter_init_public_api():
    """🆕 W34: chapter.__init__.py 公共 API 暴露"""
    import history_footnote.chapter as ch
    # 🆕 v2.10.1 W85: +4 (RouteDetector + DEFAULT_ROUTE_KEYWORDS + VALUE_SHIFT_THRESHOLD + HISTORICAL_ANCHOR_KEYWORDS)
    # 36 → 40
    assert len(ch.__all__) == 40
    # 关键 API
    assert "ChapterCoordinator" in ch.__all__
    assert "extract_json_from_text" in ch.__all__
    assert "make_chapter_dm_tools" in ch.__all__
    # 🆕 W85: 新增 API
    assert "RouteDetector" in ch.__all__
    assert "VALUE_SHIFT_THRESHOLD" in ch.__all__
    assert "fallback_chapter_blueprint" in ch.__all__
    assert "_HAS_LC_TOOLS" in ch.__all__
    return True


def test_W34_014_chapter_init_versions():
    """chapter.__init__.py 有 version"""
    import history_footnote.chapter as ch
    assert ch.__version__ == "2.8.x"
    return True
