"""🆕 v2.10.24 — 效果应用服务

负责应用 effects (cash_delta, flag_set, city_move 等)
"""
from __future__ import annotations

import logging
from typing import Any

from history_footnote.story_mode.constants import EFFECT_TYPES_DELTA

logger = logging.getLogger(__name__)


class EffectsService:
    """应用 voice_option.effects 到 game_state"""

    @staticmethod
    def apply(game_state: dict, effects: dict[str, Any]) -> None:
        """应用 effects dict 到 game_state

        支持:
        - *_delta: 资源增量 (cash_delta, rice_delta, debt_delta, looms_delta,
                  stamina_delta, round_delta)
        - city_move: 城市切换 (注意: 这是引用赋值, 不通过 _apply_effects 处理)
        - flag_set: 在 handle_input 中单独处理 (避免重复)
        """
        if not effects:
            return

        for k, v in effects.items():
            if k.endswith("_delta"):
                base = k[: -len("_delta")]
                # 应用 delta
                current = game_state.get(base, 0) or 0
                try:
                    new_val = current + int(v)
                    game_state[base] = new_val
                except (TypeError, ValueError) as e:
                    logger.warning(f"effects.{k}={v} failed: {e}")
            elif k in ("city_move", "flag_set"):
                # city_move: handle_input 单独处理 (避免此处副作用)
                # flag_set: handle_input 单独处理 (避免重复)
                pass
            else:
                logger.debug(f"unknown effect: {k}={v}")

    @staticmethod
    def apply_flag_set(game_state: dict, flags: list[str]) -> list[str]:
        """应用 flag_set, 返回新增的 flag 列表"""
        existing = set(game_state.get("scripted_flags") or [])
        added = []
        for f in flags:
            if f not in existing:
                existing.add(f)
                added.append(f)
        game_state["scripted_flags"] = list(existing)
        return added

    @staticmethod
    def apply_city_move(game_state: dict, new_city: str) -> None:
        """应用 city_move"""
        game_state["city"] = new_city