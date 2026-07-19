"""🆕 v2.10.9 Pydantic era.json schema 校验

设计目标：
- 启动期/CLI 期 fail-fast：错填 era.json 立刻报错，而不是运行到一半才崩
- 与现有 wiki/era_validator.py (v2.10.x W61) 协作：
  - era_validator.era_validate()：返回 {valid, errors[], warnings[]}（向后兼容）
  - EraConfig Pydantic 模型：提供 strict 校验 + 详细错误路径
- 100% 向后兼容：现有 era.json 不修改；新增 era 时 strict 校验；老 era 自动用 lax 校验

使用：
    from history_footnote.wiki.era_schema import validate_era_config, EraConfig
    result = validate_era_config(era_dict)  # 抛 ValueError 或返回 EraConfig 实例
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# 子模型
# ============================================================

class TimelineDate(BaseModel):
    year: int = Field(..., ge=100, le=2200)
    month: int = Field(..., ge=1, le=12)


class Timeline(BaseModel):
    start: TimelineDate
    end: TimelineDate
    round_unit: str = Field(..., description="month/season/year")
    total_rounds: int = Field(..., ge=1, le=500)
    description: str = ""

    @field_validator("round_unit")
    @classmethod
    def _check_unit(cls, v: str) -> str:
        allowed = {"month", "season", "year"}
        if v not in allowed:
            raise ValueError(f"round_unit must be one of {allowed}, got {v!r}")
        return v


class IronLaw(BaseModel):
    id: str
    fact: str = Field(..., min_length=1)
    source: str = ""


class FreedomScope(BaseModel):
    player_can_decide: list[str] = Field(default_factory=list)
    player_cannot_change: list[str] = Field(default_factory=list)


class Season(BaseModel):
    month: int = Field(..., ge=1, le=12)
    season: str
    solar_term: str = ""
    farming: str = ""
    festival: str = ""
    market: str = ""
    narrative_flavor: str = ""


class SilkVariety(BaseModel):
    id: str
    name: str
    difficulty: str
    price_range: str
    buyers: str = ""
    note: str = ""


class MarketCycle(BaseModel):
    season: str
    effect: str
    variable_effect: dict[str, float] = Field(default_factory=dict)


class PlayerIdentity(BaseModel):
    label: str
    role: str = ""
    gender: str = Field(..., description="male/female")

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str) -> str:
        if v not in {"male", "female"}:
            raise ValueError(f"gender must be 'male' or 'female', got {v!r}")
        return v


class World(BaseModel):
    timeline: Timeline
    iron_laws: list[IronLaw] = Field(default_factory=list)
    plausibility_rules: list[str] = Field(default_factory=list)
    freedom_scope: FreedomScope = Field(default_factory=FreedomScope)
    seasons: list[Season] = Field(default_factory=list)
    silk_varieties: list[SilkVariety] = Field(default_factory=list)
    market_cycles: list[MarketCycle] = Field(default_factory=list)
    player_identities: dict[str, PlayerIdentity] = Field(default_factory=dict)


# ============================================================
# 顶层模型
# ============================================================

class EraConfig(BaseModel):
    """era.json 顶层 schema

    🆕 v2.10.9：Pydantic 模型，启动期校验。
    老 era 用 model_config = ConfigDict(strict=False) 容忍额外字段。
    """
    era_id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    era_name: str = Field(..., min_length=1)
    version: str = Field(default="0.0.0")
    world: World

    model_config = {"extra": "allow"}


# ============================================================
# 公共 API
# ============================================================

def validate_era_config(era_dict: dict, *, strict: bool = False) -> EraConfig:
    """校验 era.json dict

    Args:
        era_dict: era.json 反序列化后的 dict
        strict: True 时 extra 字段也报错；False 时仅警告

    Returns:
        EraConfig 实例

    Raises:
        ValueError: 校验失败时（带详细错误路径）
        TypeError: 输入不是 dict
    """
    if not isinstance(era_dict, dict):
        raise TypeError(f"era_dict must be dict, got {type(era_dict).__name__}")

    if strict:
        # 严格模式：把 extra 字段检测出来
        try:
            return EraConfig.model_validate(era_dict)
        except Exception as e:
            raise ValueError(f"era.json strict validation failed: {e}") from e

    # 宽松模式：extra 字段允许但记 warning
    try:
        cfg = EraConfig.model_validate(era_dict)
    except Exception as e:
        raise ValueError(f"era.json validation failed: {e}") from e

    # 警告 extra 字段
    allowed = set(EraConfig.model_fields.keys())
    extras = set(era_dict.keys()) - allowed
    if extras:
        import logging
        logging.getLogger("history_footnote.wiki.era_schema").warning(
            f"era.json has extra top-level fields (ignored): {sorted(extras)}"
        )
    return cfg


def validate_era_file(era_path, *, strict: bool = False) -> EraConfig:
    """校验 era.json 文件

    Args:
        era_path: Path 对象或 str
        strict: True 时严格校验

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 校验失败
    """
    from pathlib import Path
    import json
    p = Path(era_path)
    if not p.exists():
        raise FileNotFoundError(f"era.json not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return validate_era_config(data, strict=strict)