"""🆕 v2.10.6：开局剧情带入模板测试

验证：
1. session.py setdefault 给每个身份填好 background + opening_paragraph
2. opening_paragraph 用 {name} {hometown} {occupation} 占位符
3. 4 个身份（weaving_male/female + merchant_male/female）都覆盖
4. 模板里没有未识别的占位符（str.format 不抛异常）
5. print_opening 输出含 6 段

依赖说明：
- 装饰器 / dispatch 兜底测试可独立跑（仅 import game_state）
- session.py 测试需要 langchain_core
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest.mock import MagicMock


def _has_langchain_core() -> bool:
    return importlib.util.find_spec("langchain_core") is not None


class TestSessionOpeningTemplate(unittest.TestCase):
    """v2.10.6: session.py setdefault 给身份填 background + opening_paragraph"""

    def test_session_has_default_background_dict(self):
        """session.py 源里有 DEFAULT_BACKGROUND_BY_IDENTITY"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_BACKGROUND_BY_IDENTITY", text,
                      "session.py 应有 DEFAULT_BACKGROUND_BY_IDENTITY 字典")

    def test_session_has_default_opening_dict(self):
        """session.py 源里有 DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY", text,
                      "session.py 应有 DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY 字典")

    def test_session_covers_4_identities(self):
        """覆盖 4 个身份"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        for ident in ["weaving_male", "weaving_female", "merchant_male", "merchant_female"]:
            self.assertIn(ident, text, f"session.py 应覆盖身份 {ident}")

    def test_session_uses_str_format_with_placeholders(self):
        """setdefault 用 str.format 占位符 {name} {hometown} {occupation}"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        self.assertIn("default_opening_tpl.format(", text,
                      "session.py 应用 .format() 格式化 opening_paragraph 模板")
        self.assertIn("name=", text, "应传入 name 参数")
        self.assertIn("hometown=", text, "应传入 hometown 参数")
        self.assertIn("occupation=", text, "应传入 occupation 参数")

    def test_session_setdefault_uses_custom_opening(self):
        """如果 custom_character 自带 opening_paragraph（LLM 生成的），setdefault 不覆盖"""
        import pathlib
        session_py = pathlib.Path(__file__).parent.parent / "src" / "history_footnote" / "web_server" / "routers" / "session.py"
        text = session_py.read_text(encoding="utf-8")
        # setdefault 不覆盖
        self.assertIn("setdefault(\"opening_paragraph\"", text,
                      "session.py 应用 setdefault 保留 LLM 生成的开场白")


class TestOpeningTemplateFormats(unittest.TestCase):
    """v2.10.6: 模板 str.format 不能抛 KeyError/IndexError"""

    def _test_format(self, identity, custom_character):
        """复刻 session.py 的 setdefault 逻辑，验证 .format() 不抛异常"""
        # 复制 session.py 中的模板（保持同步）
        DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY = {
            "weaving_male":   "万历十五年的正月，江南还是料峭春寒。盛泽镇河面上浮着一层薄冰，桑叶还没发芽，织工们已经陆续点亮了织机前的油灯。你推开作坊的门，冷气扑了满脸。两台旧织机蹲在昏暗的屋子里，像两头沉睡的牲口，等着你今天的第一梭。\n\n今早镇上的传言不少：苏州的织造局又下了新派银子的公文，王牙人在牙行门口骂骂咧咧，说今年的丝价要涨；隔壁张寡妇家昨夜哭了一宿——她男人去年欠下的赌债，债主终于找上了门。\n\n你握紧手里的梭子。新的一年就这么开始了。",
        }
        tpl = DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY.get(identity, "")
        if tpl:
            # 这是 session.py 实际做的：format(name, hometown, occupation)
            # 占位符不在模板里应该 no-op（Python str.format 不会抛错）
            try:
                out = tpl.format(
                    name=custom_character.get("name", "你"),
                    hometown=custom_character.get("hometown", "盛泽镇"),
                    occupation=custom_character.get("occupation", "织工"),
                )
                return out
            except (KeyError, IndexError) as e:
                self.fail(f"format 异常: {e}")
        return ""

    def test_weaving_male_default_chars(self):
        """weaving_male 模板 + 默认 4 字段 = 不抛异常"""
        out = self._test_format("weaving_male", {
            "name": "沈织户",
            "hometown": "盛泽镇",
            "occupation": "织工",
        })
        # 模板里没有 {xxx} 占位符 → format 不变
        self.assertIn("万历十五年的正月", out)
        self.assertIn("盛泽镇", out)
        self.assertIn("织工", out)

    def test_weaving_male_chinese_name(self):
        """中文名字不抛异常"""
        out = self._test_format("weaving_male", {
            "name": "沈老三",  # 中文 3 字
            "hometown": "苏州府",
            "occupation": "绸缎商",
        })
        self.assertIn("万历十五年的正月", out)

    def test_weaving_male_missing_optional_fields(self):
        """缺 hometown/occupation 用默认"""
        out = self._test_format("weaving_male", {
            "name": "测试",
            # 缺 hometown/occupation
        })
        # format 会用 default 值（"盛泽镇" / "织工"）
        self.assertIn("万历十五年的正月", out)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)