"""🆕 v2.10.x W61: era.json 验证器

验证 era 配置完整性
- era_validate(era_config) → {valid, errors[], warnings[]}
- era_required_fields() → [field names]
"""
from __future__ import annotations
from typing import Any

REQUIRED_FIELDS = [
    "era_id",
    "title",
    "year",
    "narrative",
    "characters",
    "fate_cards",
]

OPTIONAL_FIELDS = [
    "description",
    "cover_image",
    "scenes",
    "chapter_settings",
    "tags",
]


def era_validate(era_config: dict | None) -> dict:
    """验证 era 配置

    Returns:
        {
            "valid": bool,
            "errors": [...],
            "warnings": [...],
        }
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not era_config or not isinstance(era_config, dict):
        return {"valid": False, "errors": ["era_config must be a dict"], "warnings": []}

    # 必填字段
    for field in REQUIRED_FIELDS:
        if field not in era_config:
            errors.append(f"missing required field: {field}")
        elif not era_config[field]:
            errors.append(f"required field empty: {field}")

    # narrative 必填子字段
    narrative = era_config.get("narrative", {})
    if isinstance(narrative, dict):
        for sub in ["setting", "tone", "main_conflict"]:
            if sub not in narrative or not narrative[sub]:
                warnings.append(f"narrative.{sub} recommended")

    # characters 应为列表
    characters = era_config.get("characters", [])
    if not isinstance(characters, list) or len(characters) == 0:
        errors.append("characters must be non-empty list")
    else:
        for i, char in enumerate(characters):
            if not isinstance(char, dict):
                errors.append(f"characters[{i}] must be dict")
                continue
            if "id" not in char:
                errors.append(f"characters[{i}] missing id")
            if "name" not in char:
                errors.append(f"characters[{i}] missing name")

    # fate_cards 应为列表
    fate_cards = era_config.get("fate_cards", [])
    if not isinstance(fate_cards, list):
        errors.append("fate_cards must be list")
    else:
        for i, card in enumerate(fate_cards):
            if not isinstance(card, dict):
                errors.append(f"fate_cards[{i}] must be dict")
                continue
            if "id" not in card:
                errors.append(f"fate_cards[{i}] missing id")

    # chapter_settings 校验（如有）
    chapter_settings = era_config.get("chapter_settings", {})
    if chapter_settings:
        total = chapter_settings.get("total_chapters")
        if total is not None and (not isinstance(total, int) or total < 1 or total > 50):
            warnings.append(f"chapter_settings.total_chapters {total} 异常（应在 1-50）")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def era_required_fields() -> list[str]:
    return list(REQUIRED_FIELDS)


def era_optional_fields() -> list[str]:
    return list(OPTIONAL_FIELDS)


def era_fix(era_config: dict) -> dict:
    """自动修复（填充默认值）"""
    if not isinstance(era_config, dict):
        return era_config
    fixed = dict(era_config)
    if "narrative" not in fixed or not fixed["narrative"]:
        fixed["narrative"] = {"setting": "", "tone": "", "main_conflict": ""}
    if "tags" not in fixed:
        fixed["tags"] = []
    return fixed
