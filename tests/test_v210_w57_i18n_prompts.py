"""🆕 v2.10.x W57: 多语言 prompt 测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))



def test_W57_001_supported_locales():
    from history_footnote.i18n_prompts import SUPPORTED_LOCALES
    assert "zh-CN" in SUPPORTED_LOCALES
    assert "en-US" in SUPPORTED_LOCALES


def test_W57_002_chapter_blueprint_zh():
    from history_footnote.i18n_prompts import get_chapter_blueprint_prompt
    p = get_chapter_blueprint_prompt("zh-CN", chapter=1, total_chapters=10, era_id="wanli1587", identity="weaving_male")
    assert "第 1 章" in p
    assert "wanli1587" in p
    assert "10" in p


def test_W57_003_chapter_blueprint_en():
    from history_footnote.i18n_prompts import get_chapter_blueprint_prompt
    p = get_chapter_blueprint_prompt("en-US", chapter=3, total_chapters=5, era_id="hongwu1399", identity="scholar")
    assert "Chapter 3" in p
    assert "hongwu1399" in p


def test_W57_004_chapter_settlement_zh():
    from history_footnote.i18n_prompts import get_chapter_settlement_prompt
    p = get_chapter_settlement_prompt("zh-CN", chapter=5)
    assert "第 5 章" in p
    assert "summary" in p


def test_W57_005_chapter_settlement_en():
    from history_footnote.i18n_prompts import get_chapter_settlement_prompt
    p = get_chapter_settlement_prompt("en-US", chapter=2)
    assert "Chapter 2" in p


def test_W57_006_narrative_continuation_both():
    from history_footnote.i18n_prompts import get_narrative_continuation_prompt
    p_zh = get_narrative_continuation_prompt("zh-CN", action="驻足倾听", scene="茶馆", status="疲惫")
    p_en = get_narrative_continuation_prompt("en-US", action="listen", scene="teahouse", status="tired")
    assert "驻足倾听" in p_zh
    assert "listen" in p_en
