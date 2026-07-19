"""🆕 v2.10.9 P2-2: 验证 views/ 不再反向依赖 routers/ + fallback voices 单元测试"""
from __future__ import annotations

import ast
from pathlib import Path


def test_views_does_not_import_routers():
    """views/ 层不应 import routers/ 层（防止循环依赖）"""
    views_dir = Path("src/history_footnote/web_server/views")
    bad: list[str] = []
    pattern = "history_footnote.web_server.routers"

    for py_file in views_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(pattern):
                    bad.append(f"{py_file}:{node.lineno}: {ast.dump(node.module)}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(pattern):
                        bad.append(f"{py_file}:{node.lineno}: {alias.name}")

    assert not bad, "views/ 层不应 import routers/ 层：\n" + "\n".join(bad)


def test_load_fallback_voices_empty():
    """空文本 → 空列表"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    assert _load_fallback_voices("") == []


def test_load_fallback_voices_money_keyword():
    """含银/钱/税 → 应包含算盘声"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices("此时账上还有银子三两")
    assert any(v["voice_id"] == "voice_accountant" for v in voices), \
        "应包含 voice_accountant"


def test_load_fallback_voices_official_keyword():
    """含官/里长 → 应包含本分"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices("赵里长亲自上门催税")
    assert any(v["voice_id"] == "voice_compliance" for v in voices)


def test_load_fallback_voices_weaving_keyword():
    """含织/布/丝 → 应包含手艺人的骄傲"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices("织机又卡了，得换梭子")
    assert any(v["voice_id"] == "voice_craft" for v in voices)


def test_load_fallback_voices_no_keyword():
    """无关键字 → 应只含 3 个兜底选项"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices("今天天气不错")
    assert len(voices) == 3
    ids = {v["voice_id"] for v in voices}
    assert ids == {"voice_observed", "voice_action", "voice_ask"}


def test_load_fallback_voices_max_three():
    """即使 4 个关键字都命中，最多返回 3 个 voice"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices(
        "银钱税都齐了，官府里长也来了，织布的活儿忙完，该去牙行王掌柜那里"
    )
    assert len(voices) <= 3, f"最多 3 个，实际 {len(voices)}"


def test_load_fallback_voices_no_duplicates():
    """不应有重复 voice_id"""
    from history_footnote.web_server.views.session import _load_fallback_voices
    voices = _load_fallback_voices("银钱税官府里长织布丝牙行王掌柜客商")
    ids = [v["voice_id"] for v in voices]
    assert len(ids) == len(set(ids)), f"有重复 voice_id: {ids}"