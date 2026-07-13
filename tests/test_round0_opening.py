"""🆕 v2.10.4-patch3：第 0 回合 opening 格式 + type 字段测试

验证：
1. round 0 narrative 的 type 字段 = "opening"（v2.10.4-patch3 新增）
2. round 0 文本格式符合 [game_loop_display.py] print_opening() 输出：
   - "欢迎来到【万历十五年】" + 性别符号
   - "你是 沈织户 — 盛泽镇"
   - "【开局处境】" + 兜底文案
   - "日期：1587年1月"
3. 后续回合的 type 默认是 "response"（向后兼容）
4. format_state 把 type 字段透传到 recent_narratives

依赖说明：
- 装饰器 / dispatch 兜底测试可独立跑（仅 import game_state）
- session.py / start 流程测试需要 langchain_core 在环境里
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import fields


def _has_langchain_core() -> bool:
    return importlib.util.find_spec("langchain_core") is not None


def _make_game_state(identity="weaving_male", gender="male", custom=None):
    """构造一个最小可用的 GameState 用于测试 opening

    round=0 测试只需要 GameState 基础字段（不需要 era_config 完整加载）
    """
    from history_footnote.game_state import GameState
    gs = GameState(round_number=0, era_id="wanli1587")
    if custom:
        gs.custom_character.update(custom)
    gs.custom_character.setdefault("name", "沈织户")
    gs.custom_character.setdefault("hometown", "盛泽镇")
    gs.custom_character.setdefault("occupation", "织工")
    return gs


class TestAppendNarrativeType(unittest.TestCase):
    """v2.10.4-patch3: append_narrative 支持 type 字段"""

    def setUp(self):
        from history_footnote.game_state import GameState
        self.gs = GameState(round_number=0, era_id="wanli1587")

    def test_default_type_is_response(self):
        """默认 type = 'response'（向后兼容）"""
        self.gs.append_narrative(1, "narrative text", "summary")
        self.assertEqual(self.gs.narrative_recent[0]["type"], "response")

    def test_explicit_type_opening(self):
        """显式传 narrative_type='opening'"""
        self.gs.append_narrative(0, "opening text", "开场", narrative_type="opening")
        self.assertEqual(self.gs.narrative_recent[0]["type"], "opening")

    def test_explicit_type_system(self):
        """显式传 narrative_type='system'（系统提示）"""
        self.gs.append_narrative(99, "system msg", "系统", narrative_type="system")
        self.assertEqual(self.gs.narrative_recent[0]["type"], "system")

    def test_other_fields_preserved(self):
        """type 不影响其他字段"""
        self.gs.append_narrative(
            5, "story", "summary",
            player_input="我去苏州",
            chosen_voice="起身上路",
            current_date="1587年2月",
            chapter_id=2,
            narrative_type="story",
        )
        entry = self.gs.narrative_recent[0]
        self.assertEqual(entry["round"], 5)
        self.assertEqual(entry["player_input"], "我去苏州")
        self.assertEqual(entry["chosen_voice"], "起身上路")
        self.assertEqual(entry["current_date"], "1587年2月")
        self.assertEqual(entry["chapter_id"], 2)
        self.assertEqual(entry["type"], "story")


class TestOpeningTextFormat(unittest.TestCase):
    """验证 round 0 opening 文本格式（[game_loop_display.py] print_opening 输出）

    文本格式（v1.5.1+ 玩家在向导中由 LLM 生成人设）：
      欢迎来到【万历十五年】 ♂/♀
      你是 沈织户 — 盛泽镇
      【开局处境】今早推开家门，织工的活计照旧，但心里总有些不安。
      日期：1587年1月
    """

    @staticmethod
    def _call_print_opening(player_gender="male", custom_character=None, era_id="wanli1587", identity="weaving_male"):
        """直接调 print_opening，返回输出文本（不依赖 GameLoop）"""
        import io
        from contextlib import redirect_stdout
        from history_footnote import game_loop_display

        era_config = {"era_name": "万历十五年"}
        identity_config = {"label": "织户"}

        # print_opening 接受 state 对象，需要有 player_gender + custom_character 属性
        from unittest.mock import MagicMock
        state = MagicMock()
        state.player_gender = player_gender
        state.custom_character = custom_character or {
            "name": "沈织户",
            "hometown": "盛泽镇",
            "occupation": "织工",
            "starting_situation": "今早推开家门，织工的活计照旧，但心里总有些不安。",
        }
        # print_opening 不向 state 写东西，但 state 需有 month / era 等
        state.current_date = "1587年1月"

        buf = io.StringIO()
        with redirect_stdout(buf):
            game_loop_display.print_opening(
                state=state,
                era_config=era_config,
                identity_config=identity_config,
                era_id=era_id,
                selected_identity=identity,
            )
        return buf.getvalue()

    def test_opening_has_required_lines(self):
        """验证 opening 文本含 7 个必备段"""
        text = self._call_print_opening(player_gender="male")
        # 7 个必备段（v2.10.4 用户确认）
        self.assertIn("欢迎来到【万历十五年】", text)
        self.assertIn("♂", text)  # 男性
        self.assertIn("沈织户", text)
        self.assertIn("盛泽镇", text)
        self.assertIn("【开局处境】", text)
        self.assertIn("织工", text)
        self.assertIn("日期：1587年1月", text)

    def test_opening_female_uses_venus(self):
        """female 性别使用 ♀"""
        text = self._call_print_opening(
            player_gender="female",
            custom_character={
                "name": "林织娘",
                "hometown": "盛泽镇",
                "occupation": "织工",
                "starting_situation": "今早推开家门，织工的活计照旧，但心里总有些不安。",
            },
            identity="weaving_female",
        )
        self.assertIn("林织娘", text)
        self.assertIn("♀", text)
        self.assertNotIn("♂", text)


@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import format_state")
class TestFormatStateRound0(unittest.TestCase):
    """验证 format_state 把 round 0 的 type="opening" 透传到 recent_narratives"""

    @staticmethod
    def _make_fake_game(narrative_history):
        """构造一个 format_state 用的 fake game object"""
        from unittest.mock import MagicMock
        game = MagicMock()
        # format_state 内部访问 game.state.narrative_history 和 game.state.append_narrative 等
        state = MagicMock()
        state.narrative_history = list(narrative_history)
        state.round_number = narrative_history[-1].get("round", 0) if narrative_history else 0
        state.action_points = 0
        state.value_shifts = {}
        state.active_tasks = []
        state.completed_tasks = []
        state.fate_hand = []
        state.used_fate_cards = []
        state.current_date = "1587年1月"
        state.selected_identity = "weaving_male"
        state.player_gender = "male"
        state.npc_relations = {}
        state.recent_discoveries = []
        state.character_wiki = {}
        state.known_facts = []
        state.last_voice_options = []
        game.state = state
        game.session = MagicMock()
        game.session.session_id = "test-session-001"
        game.era_id = "wanli1587"
        game.era_config = {"era_name": "万历十五年"}
        # 一些其他字段 stub
        game.active_quests = []
        game.available_quests = []
        return game

    def test_round0_type_opening(self):
        from history_footnote.web_server.views.format_state import format_state

        history = [
            {"round": 0, "narrative": "mock opening", "summary": "开场", "type": "opening"},
        ]
        game = self._make_fake_game(history)
        state = format_state(game)
        recents = state["recent_narratives"]
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["type"], "opening")
        self.assertEqual(recents[0]["round"], 0)

    def test_round1_type_response(self):
        from history_footnote.web_server.views.format_state import format_state

        history = [
            {"round": 1, "narrative": "mock story", "summary": "summary1", "type": "response"},
        ]
        game = self._make_fake_game(history)
        state = format_state(game)
        recents = state["recent_narratives"]
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["type"], "response")

    def test_recent_narratives_includes_type(self):
        """recent_narratives 列表里每条都带 type"""
        from history_footnote.web_server.views.format_state import format_state

        history = [
            {"round": 0, "narrative": "opening", "summary": "开场", "type": "opening"},
            {"round": 1, "narrative": "round1", "summary": "summary1", "type": "response"},
            {"round": 2, "narrative": "round2", "summary": "summary2", "type": "story"},
        ]
        game = self._make_fake_game(history)
        state = format_state(game)
        recents = state["recent_narratives"]
        # recent_narratives 顺序是 [oldest, ..., latest]（取最后 3 条，按 narrative_history 顺序）
        self.assertEqual(len(recents), 3)
        self.assertEqual(recents[0]["type"], "opening")
        self.assertEqual(recents[1]["type"], "response")
        self.assertEqual(recents[2]["type"], "story")


@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import era_config_loader")
class TestSessionStartOpeningType(unittest.TestCase):
    """验证 session.py handle_POST_start 调用时传 type='opening'"""

    def test_session_calls_opening_with_type(self):
        """读 session.py 源码验证：append_narrative 调用时传 narrative_type='opening'"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        # 找到 opening 时的 append_narrative 调用
        self.assertIn("narrative_type=\"opening\"", text,
                      "session.py 应该在 opening narrative append 时传 narrative_type='opening'")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)