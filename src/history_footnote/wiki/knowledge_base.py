"""知识库——四层存储 + 场景触发注入

设计参考：设计文档v1.0.md 第3.4节"知识库"

四层存储：
- background: 时代背景（游戏开始时全量注入）
- scene: 场景知识（场景切换时检索注入）
- entity: 实体档案（NPC/地点出场时检索注入）
- principle: 原理/制度（玩家输入含关键词时注入）

Phase 1.1 增强：支持 narrative_snippets（闲谈素材）
- entries：抽象知识（背景、场景、实体、原理）
- snippets：叙事片段（小说原文、场景描写、NPC对白）

Phase 1用关键词匹配检索，Phase 2可升级为embedding+向量数据库。
百级别条目不需要向量数据库。
"""
from __future__ import annotations

import re
from typing import Any


class KnowledgeBase:
    """知识库检索器

    Phase 1.1 增强：支持 narrative_snippets（闲谈素材）
    - entries：抽象知识（背景、场景、实体、原理）
    - snippets：叙事片段（小说原文、场景描写、NPC对白）
    """

    def __init__(
        self,
        entries: list[dict],
        snippets: list[dict] | None = None,
        story_segments: dict[str, list[dict]] | None = None,
    ):
        self.entries = entries
        self.snippets = snippets or []
        self.story_segments = story_segments or {}
        self.by_id = {e["id"]: e for e in entries}
        self.snippets_by_id = {s["id"]: s for s in self.snippets}
        self.by_layer: dict[str, list[dict]] = {}
        for e in entries:
            layer = e.get("layer", "principle")
            self.by_layer.setdefault(layer, []).append(e)

    def get_background(self) -> list[dict]:
        """获取所有background条目（游戏开始时全量注入）"""
        return self.by_layer.get("background", [])

    def query(
        self,
        keywords: list[str] | None = None,
        scene: str = "",
        layer: str = "",
        entry_ids: list[str] | None = None,
    ) -> list[dict]:
        """查询知识库条目

        Args:
            keywords: 关键词列表，匹配条目trigger_keywords
            scene: 场景名，匹配trigger_scene
            layer: 限定层级（background/scene/entity/principle）
            entry_ids: 直接指定要获取的条目ID（用于insight解锁时获取相关知识）

        Returns:
            匹配的条目列表
        """
        # 直接按ID查询（insight解锁使用）
        if entry_ids:
            return [self.by_id[eid] for eid in entry_ids if eid in self.by_id]

        # 🆕 v1.7.28 修复：空查询守卫
        # 没有任何过滤条件时，禁止返回全部条目（避免炸库 + 上下文爆炸）
        # 必须至少有：keywords / scene / layer 之一
        if not keywords and not scene and not layer:
            return []

        # 关键词过滤：必须是有效中文 2-4 字 token 才参与匹配
        # 避免"嗯"/"好"/标点等无意义输入穿透
        if keywords:
            keywords = [kw for kw in keywords if kw and len(kw) >= 2]
            if not keywords and not scene and not layer:
                return []

        results = []
        for entry in self.entries:
            if layer and entry.get("layer") != layer:
                continue

            # 场景匹配
            if scene:
                trigger_scenes = entry.get("trigger_scene", [])
                if trigger_scenes and scene not in trigger_scenes:
                    continue

            # 关键词匹配
            if keywords:
                trigger_kws = entry.get("trigger_keywords", [])
                if not any(kw in trigger_kws or kw in entry.get("content", "") for kw in keywords):
                    continue

            results.append(entry)

        # 🆕 v1.7.29 修复塌房 3：layer 优先级排序
        # 原因：旧逻辑返回顺序 = entries 列表顺序，"朝廷" 一次命中 7 条
        # LLM 不知道哪条优先，可能乱用导致剧透
        # 新逻辑：按 layer 优先级（background > principle > scene > entity）
        # + 关键词命中数评分
        def sort_key(e):
            layer = e.get("layer", "entity")
            layer_priority = {
                "background": 0,    # 时代背景 → 最高优先（最普适）
                "principle": 1,      # 制度/原理 → 高（提供时代逻辑）
                "scene": 2,          # 场景知识 → 中（提供当下细节）
                "entity": 3,         # 人物/地点 → 低（容易剧透）
            }
            layer_score = layer_priority.get(layer, 4)
            # 关键词命中数（越多越相关）
            hit_count = 0
            if keywords:
                for kw in keywords:
                    if kw in e.get("trigger_keywords", []) or kw in e.get("content", ""):
                        hit_count += 1
            # 排序：先按 layer 优先级，再按 hit_count 倒序
            return (layer_score, -hit_count)

        results.sort(key=sort_key)
        return results

    def search_by_text(self, text: str, top_k: int = 3) -> list[dict]:
        """基于文本的简单检索（Phase 1简化版）

        提取文本中的关键词，与条目trigger_keywords匹配。
        """
        keywords = self._extract_keywords(text)
        if not keywords:
            return []
        return self.query(keywords=keywords)[:top_k]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """提取关键词（简单实现：2-4字的中文token）"""
        # 简单分词：2-4字中文字符串
        keywords = set()
        for match in re.finditer(r"[\u4e00-\u9fa5]{2,4}", text):
            kw = match.group()
            if len(kw) >= 2:
                keywords.add(kw)
        return list(keywords)[:10]  # 限制数量

    def get_by_id(self, entry_id: str) -> dict | None:
        return self.by_id.get(entry_id)

    # === narrative_snippets 检索 ===

    def query_snippets(
        self,
        scene: str = "",
        keywords: list[str] | None = None,
        snippet_ids: list[str] | None = None,
        top_k: int = 3,
        player_gender: str = "",
    ) -> list[dict]:
        """查询叙事片段（按场景+关键词+性别匹配）

        v1.1+：新增player_gender过滤，target_gender为"male"/"female"/"all"

        Args:
            scene: 场景名（如"茶馆"、"盛泽市集"），匹配 applies_to_scenes
            keywords: 关键词列表，匹配 trigger_keywords 或 snippet_text
            snippet_ids: 直接指定片段ID列表
            top_k: 返回前K条
            player_gender: 玩家性别（male/female），过滤掉不匹配的片段

        Returns:
            匹配的片段列表（按相关度排序）
        """
        # 直接按ID查询
        if snippet_ids:
            return [self.snippets_by_id[sid] for sid in snippet_ids if sid in self.snippets_by_id]

        if not self.snippets:
            return []

        scored = []
        for snip in self.snippets:
            # 性别过滤
            if player_gender:
                target_gender = snip.get("target_gender", "all")
                if target_gender not in ("all", player_gender):
                    continue

            score = 0

            # 场景匹配（最相关）
            if scene:
                applies = snip.get("applies_to_scenes", [])
                if scene in applies:
                    score += 10
                elif applies and any(s in scene for s in applies):
                    score += 3

            # 关键词匹配
            if keywords:
                trigger_kws = snip.get("trigger_keywords", [])
                matched = sum(1 for kw in keywords if kw in trigger_kws or kw in snip.get("snippet_text", ""))
                score += matched * 2

            if score > 0:
                scored.append((score, snip))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]

    def query_segments(
        self,
        scene: str = "",
        segment_type: str = "",
        keywords: list[str] | None = None,
        top_k: int = 3,
    ) -> list[dict]:
        """查询story_segments（按场景+类型+关键词）

        v1.2+：DND分段叙事。每条segment是独立的叙事片段，
        LLM按需检索+自由组合生成故事。

        Args:
            scene: 场景名（如"盛泽市集"）
            segment_type: 片段类型（atmosphere/npc_dialog/transaction/rumor/description）
            keywords: 关键词列表
            top_k: 返回前K条

        Returns:
            匹配的segments列表
        """
        segments_by_scene = self.story_segments.get(scene, [])
        if not segments_by_scene:
            return []

        scored = []
        for seg in segments_by_scene:
            score = 0

            # 类型匹配（最相关）
            if segment_type and seg.get("type") == segment_type:
                score += 5

            # 关键词匹配
            if keywords:
                seg_kws = seg.get("keywords", [])
                matched = sum(1 for kw in keywords if kw in seg_kws or kw in seg.get("text", ""))
                score += matched

            # 默认给所有片段一个基础分（确保返回）
            if not segment_type and not keywords:
                score = 1

            if score > 0:
                scored.append((score, seg))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]

    def get_random_segment(self, scene: str, segment_type: str = "") -> dict | None:
        """从指定场景随机抽取一条segment

        Args:
            scene: 场景名
            segment_type: 可选的类型过滤

        Returns:
            随机segment或None
        """
        segments = self.story_segments.get(scene, [])
        if not segments:
            return None

        if segment_type:
            filtered = [s for s in segments if s.get("type") == segment_type]
            if filtered:
                segments = filtered

        import random
        return random.choice(segments) if segments else None

    def detect_scene(self, text: str) -> str:
        """根据玩家输入自动检测当前场景

        简化实现：关键词映射
        """
        scene_keywords = {
            "茶馆": ["茶馆", "喝茶", "听说", "听人聊", "闲谈", "八卦"],
            "牙行": ["牙行", "卖绸", "买丝", "行情", "牙人", "客商机"],
            "盛泽市集": ["集市", "市集", "上街", "出门", "去市里", "镇上"],
            "自家作坊": ["织机", "缫丝", "作坊", "织布", "理经", "在家里"],
            "镇外桑田": ["桑田", "桑叶", "养蚕", "蚕", "出镇", "村外", "借宿", "农家"],
            "县衙": ["县衙", "知县", "官府", "告状", "里长", "里老", "催税", "税单"],
        }

        for scene, kws in scene_keywords.items():
            if any(kw in text for kw in kws):
                return scene
        return ""

    def get_snippet_by_id(self, snippet_id: str) -> dict | None:
        return self.snippets_by_id.get(snippet_id)
