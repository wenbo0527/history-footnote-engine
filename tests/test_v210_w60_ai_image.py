"""🆕 v2.10.x W60: AI 配图测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W60_001_generate():
    from history_footnote.ai_image import ai_image_generate
    img = ai_image_generate("茶馆夜谈", "国风水墨")
    assert img["url"].endswith(".webp")
    assert img["style"] == "国风水墨"


def test_W60_002_bulk():
    from history_footnote.ai_image import ai_image_bulk
    imgs = ai_image_bulk(["场景1", "场景2"])
    assert len(imgs) == 2
    assert imgs[0]["url"] != imgs[1]["url"]


def test_W60_003_extract():
    from history_footnote.ai_image import extract_image_prompts
    nar = "夜深。月光如水。周文衡抚琴而歌。" * 5
    assert len(extract_image_prompts(nar, max_count=3)) <= 3


def test_W60_004_empty_raises():
    from history_footnote.ai_image import ai_image_generate
    try:
        ai_image_generate("", "x")
        raise AssertionError("should have raised")
    except ValueError:
        pass
