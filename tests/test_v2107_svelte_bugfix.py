"""🆕 v2.10.7：修 2 个 Svelte 错误测试

错误 1: StartMenu.svelte TypeError: Cannot read properties of undefined (reading 'length')
- 根因：前端 `response.sessions`，后端返 `archives` 字段
- 修复：后端同时返 `sessions` + `archives` 字段

错误 2: ActionPanel.svelte each_key_duplicate undefined
- 根因：LLM voice_options 偶尔缺 voice_id
- 修复：mapper 兜底 voice_id（用 index 替代）

依赖说明：
- 装饰器 / dispatch 兜底测试可独立跑
- session.py 测试需要 langchain_core
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest.mock import MagicMock


def _has_langchain_core() -> bool:
    return importlib.util.find_spec("langchain_core") is not None


class TestArchivesResponseField(unittest.TestCase):
    """v2.10.7: 后端 /api/archives 同时返 sessions 字段"""

    def test_session_py_returns_sessions_field(self):
        """session.py 源里有 sessions 字段"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        self.assertIn('"sessions": out', text,
                      "session.py handle_GET_archives 应返 sessions 字段")
        # 双字段向后兼容
        self.assertIn('"archives": out', text,
                      "session.py handle_GET_archives 也应返 archives 字段（向后兼容）")
        # count 字段
        self.assertIn('"count":', text,
                      "session.py handle_GET_archives 应返 count 字段")


class TestVoiceIdFallback(unittest.TestCase):
    """v2.10.7: mapper 兜底 voice_id 防止 duplicate key"""

    def test_frontend_uses_voice_id_fallback(self):
        """mapper.ts 源里有 voice_id 兜底"""
        import pathlib
        mapper_ts = pathlib.Path(__file__).parent.parent / "src" / "frontend" / "src" / "lib" / "api" / "mapper.ts"
        text = mapper_ts.read_text(encoding="utf-8")
        # mapper 兜底 voice_id
        self.assertIn("v.voice_id || v.id ||", text,
                      "mapper.ts 应有 voice_id 兜底（用 v.id 或 voice_${i} 替代）")
        # mapper 兜底 voice_name
        self.assertIn("v.voice_name || v.name ||", text,
                      "mapper.ts 应有 voice_name 兜底")
        # mapper 兜底 intent_text
        self.assertIn("v.intent_text || v.text", text,
                      "mapper.ts 应有 intent_text 兜底")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)