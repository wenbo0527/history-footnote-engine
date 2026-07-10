"""v2.8.0 段二 ChapterMetaResolver

职责：
- 从 era.json.narrative.hero_journey_acts 读取元属性定义
- 根据 chapter_id 产出 ChapterMeta（LLM 不可改的硬约束）
- 段二纯规则引擎，0 LLM 调用

hero_journey_acts 数据结构（era.json）：
{
  "narrative": {
    "hero_journey_acts": [
      {
        "act": "departure",
        "chapters": [1, 2, 3],
        "chapter_roles": ["ordinary", "call", "threshold"],
        "emotion_tone": "unease→resolve",
        "choice_type": "whether_to_step_out"
      },
      ...
    ]
  }
}
"""
from __future__ import annotations

import logging
from typing import Optional

from history_footnote.chapter.types import ChapterMeta

_LOG = logging.getLogger("history_footnote.chapter.meta_resolver")


# 段二硬编码的 hero_journey_acts 兜底
# （如果 era.json 没配，就用这个）
DEFAULT_HERO_JOURNEY_ACTS = [
    {
        "act": "departure",
        "chapters": [1, 2, 3],
        "chapter_roles": ["ordinary", "call", "threshold"],
        "emotion_tone": "unease→resolve",
        "choice_type": "whether_to_step_out",
    },
    {
        "act": "initiation",
        "chapters": [4, 5, 6, 7],
        "chapter_roles": ["trial", "allies", "abyss_approach", "abyss"],
        "emotion_tone": "tension→awakening",
        "choice_type": "how_to_face_challenge",
    },
    {
        "act": "return",
        "chapters": [8, 9, 10],
        "chapter_roles": ["return_path", "ultimate_choice", "finale"],
        "emotion_tone": "clarity→transcendence",
        "choice_type": "what_i_bring_back",
    },
]


class ChapterMetaResolver:
    """章节元属性解析器

    用法：
        resolver = ChapterMetaResolver(era_config)
        meta = resolver.resolve(chapter_id=1)  # 返回 ChapterMeta
    """

    def __init__(self, era_config: dict):
        self.era_config = era_config
        self._acts = self._load_acts()

    def _load_acts(self) -> list[dict]:
        """从 era_config 加载 hero_journey_acts，缺失则用兜底"""
        narrative = self.era_config.get("narrative", {}) or {}
        acts = narrative.get("hero_journey_acts")
        if not acts:
            _LOG.warning(
                "era.json 缺 narrative.hero_journey_acts，使用段二兜底配置"
            )
            return DEFAULT_HERO_JOURNEY_ACTS
        return acts

    def resolve(self, chapter_id: int) -> ChapterMeta:
        """根据 chapter_id 产出 ChapterMeta

        流程：
        1. 在 hero_journey_acts 中找 chapter_id 对应的 act
        2. 计算该 act 内的章节索引（0-based）
        3. 用 chapter_roles[chapter_index] 作为 role
        4. act 内的 emotion_tone / choice_type 整段共享
        """
        # 找 act
        act_def = self._find_act_for_chapter(chapter_id)
        if act_def is None:
            _LOG.error("chapter_id=%d 不在任何 act 中，使用兜底", chapter_id)
            return ChapterMeta(
                chapter_id=chapter_id,
                act="departure",
                role="ordinary",
                emotion_tone="neutral",
                choice_type="open_ended",
            )

        # 找 act 内的章节索引
        chapters = act_def.get("chapters", [])
        chapter_roles = act_def.get("chapter_roles", [])
        if chapter_id not in chapters:
            _LOG.error("chapter_id=%d 不在 act '%s' 的 chapters 列表", chapter_id, act_def["act"])
            role = "ordinary"
        else:
            idx = chapters.index(chapter_id)
            role = chapter_roles[idx] if idx < len(chapter_roles) else "ordinary"

        meta = ChapterMeta(
            chapter_id=chapter_id,
            act=act_def["act"],
            role=role,
            emotion_tone=act_def.get("emotion_tone", "neutral"),
            choice_type=act_def.get("choice_type", "open_ended"),
        )
        _LOG.info(
            "ChapterMeta 解析: chapter=%d, act=%s, role=%s, emotion=%s",
            chapter_id, meta.act, meta.role, meta.emotion_tone,
        )
        return meta

    def _find_act_for_chapter(self, chapter_id: int) -> Optional[dict]:
        """在 hero_journey_acts 中找包含 chapter_id 的 act"""
        for act in self._acts:
            if chapter_id in act.get("chapters", []):
                return act
        return None

    def get_acts_summary(self) -> list[dict]:
        """获取所有 act 摘要（调试用）"""
        return [
            {
                "act": act["act"],
                "chapters": act.get("chapters", []),
                "roles": act.get("chapter_roles", []),
            }
            for act in self._acts
        ]
