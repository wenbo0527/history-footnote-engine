"""🆕 v2.10.9 era.json 加载 + Pydantic schema 校验

P1-1：从 __main__.py 下沉。
"""
from __future__ import annotations

import json
from pathlib import Path


def load_era_config(era_id: str, *, validate: bool = True, strict: bool = False) -> dict:
    """加载时代包配置

    🆕 v2.10.9 Pydantic era.json schema 校验（默认开启）：
    - validate=True：返回 dict（向后兼容），但加载时校验 schema，失败抛 ValueError
    - strict=True：extra 字段也报错（开发新 era 时建议）
    - validate=False：跳过校验（老 era 兼容 / CI 临时绕开）

    Raises:
        FileNotFoundError: era.json 不存在
        ValueError: era.json schema 校验失败
    """
    era_path = Path("eras") / era_id / "era.json"
    if not era_path.exists():
        raise FileNotFoundError(f"时代包不存在: {era_path}")
    data = json.loads(era_path.read_text(encoding="utf-8"))

    if validate:
        # 启动期 fail-fast：错填 era.json 立刻报错
        try:
            from history_footnote.wiki.era_schema import validate_era_config
            validate_era_config(data, strict=strict)
        except ValueError as e:
            # 包装错误信息，明确指出 era_id + 文件路径
            raise ValueError(
                f"era.json 校验失败 [{era_id}] {era_path}:\n{e}"
            ) from e

    return data