"""🆕 v1.7.3 DM Prompts 子包

将原 dm_agent.py 内的 system prompt 拆分到 .md 文件：
- system_base.md - 基础 system prompt（含占位符）

加载机制：
- 启动时缓存（避免每次重读）
- 模板含 {placeholder} 格式占位符
- dm_agent 在拼装时调用 fill_template() 替换

为什么用 .md：
- 可独立 review（GitHub diff 友好）
- 可被 prompt 工程师直接编辑（无需 Python 知识）
- 容易加版本控制（commit diff 看修改）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# prompts 目录
PROMPTS_DIR = Path(__file__).parent
SYSTEM_BASE_PATH = PROMPTS_DIR / "system_base.md"

# 缓存（启动时加载一次）
_SYSTEM_BASE_CACHE: str | None = None


def load_system_base() -> str:
    """加载基础 system prompt 模板（缓存）"""
    global _SYSTEM_BASE_CACHE
    if _SYSTEM_BASE_CACHE is None:
        if not SYSTEM_BASE_PATH.exists():
            raise FileNotFoundError(f"system_base.md not found: {SYSTEM_BASE_PATH}")
        _SYSTEM_BASE_CACHE = SYSTEM_BASE_PATH.read_text(encoding="utf-8")
    return _SYSTEM_BASE_CACHE


def fill_template(template: str, **kwargs: Any) -> str:
    """填充模板占位符 {key} → value

    Args:
        template: 模板字符串
        **kwargs: 占位符替换值

    Returns:
        替换后的字符串
    """
    result = template
    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        # 处理 None / list / dict 的格式化
        if value is None:
            formatted = ""
        elif isinstance(value, (list, tuple)):
            formatted = "\n".join(str(v) for v in value)
        else:
            formatted = str(value)
        result = result.replace(placeholder, formatted)
    return result


__all__ = ["load_system_base", "fill_template", "PROMPTS_DIR"]


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("DM Prompts 子包测试")
    print("=" * 50)
    tmpl = load_system_base()
    print(f"✅ load_system_base: {len(tmpl)} chars")

    # 测试 fill_template
    filled = fill_template(
        tmpl,
        era_name="万历十五年",
        recent_context="[R1] 王婆卖瓜...",
        timeline_description="明朝中后期，资本主义萌芽",
        iron_laws=["- 朱翊钧是万历帝", "- 张居正死于1582"],
        identity_role="小商人",
        identity_class="平民",
        can_access=["牙行", "茶馆"],
        cannot_access=["皇宫"],
        can_interact_with=["张顺", "丁娘子"],
        cannot_influence=["皇帝"],
        plausibility_rules=["遵循时代常识", "尊重人物性格"],
    )
    print(f"✅ fill_template: {len(filled)} chars (filled)")
    # 验证占位符都替换了
    assert "{era_name}" not in filled
    assert "万历十五年" in filled
    print("✅ 占位符全部替换")