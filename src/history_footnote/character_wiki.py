"""🆕 v1.7.1 Per-Save Character Wiki - 人物知识图谱

解决支线剧情一致性问题：
- LLM 不知道之前 NPC 说过什么 / 答应过什么
- LLM 不知道"全卖给他"和"讨价还价"分别导致了什么后果
- 玩家记不清"丁娘子是谁"

设计原则：
- Per-save（每个存档独立，不共享）
- 自动提取（LLM 输出 + 服务端 fallback 正则）
- 结构化（character / event / decision / relationship）
- 可视化（侧边栏 🕸️ 人物关系 入口）

Schema:
{
  "characters": {
    "张顺": {
      "id", "first_appear", "last_appear", "appear_count",
      "relationship", "relationship_level",
      "key_events": [...],  # 时间线
      "promises": {"我方": [...], "对方": [...]},
      "traits": [...],  # 性格特点
      "description": "...",  # 综合描述
    }
  },
  "events": [
    {"round", "type", "summary", "characters": [...]}
  ],
  "decisions": [
    {"round", "type", "summary", "alternatives": [...]}
  ],
  "relationships": {
    "张顺": {"丁娘子": "合作关系"}
  }
}

🆕 v1.7.1 关键设计：
- Wiki 只存在 GameState 里（不进数据库，不跨存档）
- 删除/重置存档 → Wiki 一起清
- 容量限制：每存档最多 50 个角色 + 200 事件（防止存档过大）
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# NPC 提取（启发式，从 narrative 文本）
# ============================================================

# 🆕 v1.7.1 NPC 称呼提取：支持"张顺"、"张顺老板"、"张顺兄"、"沈氏"等
# 关键规则：speaker 在对话开头，后面跟"说/道/答/问/笑/叹"
# 利用 narrative_renderer.DIALOGUE_RAW_PATTERN 复用
def _extract_npcs_from_narrative(narrative: str) -> list[str]:
    """从 narrative 文本提取出现过的 NPC 名称"""
    if not narrative:
        return []
    # 避免循环 import
    from history_footnote.narrative_renderer import DIALOGUE_PATTERN
    npcs = []
    seen = set()
    for speaker, _content in DIALOGUE_PATTERN.findall(narrative):
        if speaker and speaker not in seen and len(speaker) <= 6:
            # 排除动词字开头（如"心"、"我"）
            if not any(c in "我你他她它们的是了在有和与及" for c in speaker[:1]):
                npcs.append(speaker)
                seen.add(speaker)

    # 🆕 兜底：DIALOGUE_PATTERN 没识别时（用单引号），手动正则
    if not npcs:
        for m in re.finditer(
            r"([\u4e00-\u9fff]{1,6})(?:说|道|答|答道|笑道)[，：:]?['\"「『](.{4,80}?)['\"」』]",
            narrative,
        ):
            speaker = m.group(1)
            # 修剪动词字
            while speaker and speaker[-1] in "说道问答笑叹喜怒悲":
                speaker = speaker[:-1]
            if speaker and len(speaker) >= 2 and len(speaker) <= 6 and speaker not in seen:
                if not any(c in "我你他她它们的是了在有和与及" for c in speaker[:1]):
                    npcs.append(speaker)
                    seen.add(speaker)
    return npcs


# ============================================================
# Character Wiki 数据类
# ============================================================

# 角色最大数（防存档过大）
MAX_CHARACTERS = 50
# 事件最大数
MAX_EVENTS = 200
# 决策最大数
MAX_DECISIONS = 200


@dataclass
class CharacterEntry:
    """单个人物的完整记录"""
    id: str
    first_appear_round: int = 0
    first_appear_summary: str = ""
    last_appear_round: int = 0
    last_appear_summary: str = ""
    appear_count: int = 0
    relationship: str = "陌生人"  # 陌生人/熟人/朋友/仇人/...
    key_events: list[dict] = field(default_factory=list)  # 时间线
    promises_player: list[str] = field(default_factory=list)  # 我方承诺
    promises_npc: list[str] = field(default_factory=list)  # 对方承诺
    traits: list[str] = field(default_factory=list)  # 性格
    description: str = ""  # 综合描述
    created_at: int = 0  # 时间戳

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_appear_round": self.first_appear_round,
            "first_appear_summary": self.first_appear_summary,
            "last_appear_round": self.last_appear_round,
            "last_appear_summary": self.last_appear_summary,
            "appear_count": self.appear_count,
            "relationship": self.relationship,
            "key_events": self.key_events[-20:],  # 最近 20 个事件
            "promises_player": self.promises_player,
            "promises_npc": self.promises_npc,
            "traits": self.traits,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class EventEntry:
    """事件记录"""
    round: int
    type: str  # meet/deal/promise/betray/discover/...
    summary: str
    characters: list[str] = field(default_factory=list)
    timestamp: int = 0


@dataclass
class DecisionEntry:
    """关键决策记录"""
    round: int
    type: str  # negotiate/accept/refuse/attack/flee/...
    summary: str
    alternatives: list[str] = field(default_factory=list)
    consequences: str = ""  # 后续后果
    timestamp: int = 0


class CharacterWiki:
    """单存档的 Character Wiki（per-save）"""

    def __init__(self, save_id: str = ""):
        self.save_id = save_id
        self.characters: dict[str, CharacterEntry] = {}
        self.events: list[EventEntry] = []
        self.decisions: list[DecisionEntry] = []
        self.relationships: dict[str, dict[str, str]] = {}
        # NPC 关系等级映射（兼容 npc_levels）
        self.npc_levels: dict[str, str] = {}

    # ============================================================
    # 角色 CRUD
    # ============================================================

    def add_or_update_character(
        self,
        name: str,
        round: int = 0,
        summary: str = "",
        relationship: str | None = None,
        traits: list[str] | None = None,
        description: str | None = None,
    ) -> CharacterEntry:
        """添加或更新一个人物"""
        now = int(time.time() * 1000)
        if name in self.characters:
            char = self.characters[name]
            char.last_appear_round = round or char.last_appear_round
            char.last_appear_summary = summary or char.last_appear_summary
            char.appear_count += 1
            if relationship and relationship != char.relationship:
                char.relationship = relationship
            if traits:
                for t in traits:
                    if t not in char.traits:
                        char.traits.append(t)
            if description:
                char.description = description
        else:
            if len(self.characters) >= MAX_CHARACTERS:
                # 容量满：移除最久没出现的
                self._evict_oldest_character()
            char = CharacterEntry(
                id=name,
                first_appear_round=round,
                first_appear_summary=summary,
                last_appear_round=round,
                last_appear_summary=summary,
                appear_count=1,
                relationship=relationship or "陌生人",
                traits=traits or [],
                description=description or summary or name,
                created_at=now,
            )
            self.characters[name] = char
        return char

    def _evict_oldest_character(self):
        """移除最久没出现的角色（FIFO）"""
        if not self.characters:
            return
        oldest = min(
            self.characters.values(),
            key=lambda c: c.last_appear_round or 0,
        )
        del self.characters[oldest.id]

    # ============================================================
    # 事件 + 决策
    # ============================================================

    def add_event(
        self,
        round: int,
        type: str,
        summary: str,
        characters: list[str] | None = None,
    ):
        """添加事件"""
        if len(self.events) >= MAX_EVENTS:
            # 弹掉最旧的
            self.events.pop(0)
        self.events.append(EventEntry(
            round=round,
            type=type,
            summary=summary,
            characters=characters or [],
            timestamp=int(time.time() * 1000),
        ))
        # 同步更新每个角色的 key_events
        for char_name in characters or []:
            if char_name in self.characters:
                char = self.characters[char_name]
                char.key_events.append({
                    "round": round,
                    "type": type,
                    "summary": summary,
                })

    def add_decision(
        self,
        round: int,
        type: str,
        summary: str,
        alternatives: list[str] | None = None,
        consequences: str = "",
    ):
        """添加决策"""
        if len(self.decisions) >= MAX_DECISIONS:
            self.decisions.pop(0)
        self.decisions.append(DecisionEntry(
            round=round,
            type=type,
            summary=summary,
            alternatives=alternatives or [],
            consequences=consequences,
            timestamp=int(time.time() * 1000),
        ))

    def add_promise(
        self,
        character: str,
        promise: str,
        side: str = "我方",  # 我方 / 对方
    ):
        """添加承诺"""
        if character not in self.characters:
            return
        char = self.characters[character]
        if side == "我方":
            if promise not in char.promises_player:
                char.promises_player.append(promise)
        else:
            if promise not in char.promises_npc:
                char.promises_npc.append(promise)

    # ============================================================
    # 关系图
    # ============================================================

    def add_relationship(self, char1: str, char2: str, rel_type: str):
        """添加关系：char1 -> char2 = rel_type"""
        if char1 not in self.relationships:
            self.relationships[char1] = {}
        if rel_type not in self.relationships[char1].values():
            self.relationships[char1][char2] = rel_type
        # 双向
        if char2 not in self.relationships:
            self.relationships[char2] = {}
        # 简化：不维护反向（避免不一致）

    # ============================================================
    # 从 narrative 自动提取（heuristic）
    # ============================================================

    def auto_extract_from_narrative(
        self,
        narrative: str,
        round: int,
        player_input: str = "",
        player_options: list[str] | None = None,
    ):
        """🆕 v1.7.1 从 narrative 自动提取 NPC + 事件 + 决策

        启发式：
        1. 提取所有"XX 说/道..."的 speaker → add_or_update_character
        2. 提取"答应/承诺/..." → add_promise
        3. 玩家选项 → add_decision（如果有 structured input）
        """
        if not narrative:
            return

        # 1. 提取 NPC
        npcs = _extract_npcs_from_narrative(narrative)
        for npc in npcs:
            self.add_or_update_character(
                name=npc,
                round=round,
                summary=self._extract_first_appearance(narrative, npc),
            )

        # 2. 提取"答应"事件
        for npc in npcs:
            # 简化检测：npc 名字 + "答应" / "承诺" 在 50 字内
            npc_promises = self._extract_promises(narrative, npc)
            for promise in npc_promises:
                self.add_promise(npc, promise, side="对方")
                self.add_event(
                    round=round,
                    type="promise",
                    summary=f"{npc}：{promise}",
                    characters=[npc],
                )

        # 3. 玩家决策（如果传入了选项）
        if player_options and player_input:
            # 玩家实际选择的 input + 其他 alternatives
            alternatives = [opt for opt in player_options if opt != player_input]
            self.add_decision(
                round=round,
                type="choice",
                summary=player_input,
                alternatives=alternatives,
            )

    def _extract_first_appearance(self, narrative: str, npc: str) -> str:
        """提取 NPC 第一次出现的句子作为简介"""
        for sent in re.split(r"[。！？]", narrative):
            if npc in sent:
                return sent.strip()[:80]
        return npc

    def _extract_promises(self, narrative: str, npc: str) -> list[str]:
        """提取 NPC 做出的承诺（启发式）

        匹配模式：
        - "X答应/承诺/..." → 直接抓
        - "X说：'代织的事包在我身上'" → 抓引号内
        - "X同意/愿意..." → 抓后续
        """
        promises = []
        # 模式 1：X + 动词（X 是 speaker）
        for m in re.finditer(
            rf"{npc}[^。！？\n]{{0,30}}(?:答应|承诺|应允|保证|担保|同意|愿意)[^。！？\n]{{2,100}}[。！？]",
            narrative,
        ):
            promises.append(m.group(0).strip()[:80])
        # 模式 2：X + 任意动词字 + 中间可能的中文标点 + 引号内容
        # 兼容 "X答道：'...'"  "X笑道：'...'"  "X说：'...'" 等
        # 关键：动词到引号之间可能有"道" "笑" "答" + "：" 等等
        # 🆕 改用 .*?（任意字符，非贪婪）来兼容"道：" "：'..."等标点
        # 支持 4 种引号：双引号、单引号、「、『
        for m in re.finditer(
            rf"{npc}(?:说|道|答|问|笑|叹).{{0,5}}?[\"\'「『](?P<content>.{{4,80}}?)[\"\'」』]",
            narrative,
        ):
            content = m.group("content")
            if any(kw in content for kw in ["包在", "我来", "没问题", "一定", "放心", "代", "借", "卖"]):
                promises.append(f"{npc}：{content[:60]}")
        return promises[:3]  # 最多 3 个

    # ============================================================
    # 序列化
    # ============================================================

    def to_dict(self) -> dict:
        return {
            "save_id": self.save_id,
            "characters": {k: v.to_dict() for k, v in self.characters.items()},
            "events": [
                {"round": e.round, "type": e.type, "summary": e.summary, "characters": e.characters}
                for e in self.events[-50:]  # 最近 50 事件
            ],
            "decisions": [
                {"round": d.round, "type": d.type, "summary": d.summary, "alternatives": d.alternatives, "consequences": d.consequences}
                for d in self.decisions[-50:]  # 最近 50 决策
            ],
            "relationships": self.relationships,
            "stats": {
                "character_count": len(self.characters),
                "event_count": len(self.events),
                "decision_count": len(self.decisions),
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterWiki":
        wiki = cls(save_id=data.get("save_id", ""))
        for name, char_data in data.get("characters", {}).items():
            entry = CharacterEntry(
                id=char_data["id"],
                first_appear_round=char_data.get("first_appear_round", 0),
                first_appear_summary=char_data.get("first_appear_summary", ""),
                last_appear_round=char_data.get("last_appear_round", 0),
                last_appear_summary=char_data.get("last_appear_summary", ""),
                appear_count=char_data.get("appear_count", 0),
                relationship=char_data.get("relationship", "陌生人"),
                key_events=char_data.get("key_events", []),
                promises_player=char_data.get("promises_player", []),
                promises_npc=char_data.get("promises_npc", []),
                traits=char_data.get("traits", []),
                description=char_data.get("description", ""),
                created_at=char_data.get("created_at", 0),
            )
            wiki.characters[name] = entry
        for e in data.get("events", []):
            wiki.events.append(EventEntry(
                round=e["round"],
                type=e["type"],
                summary=e["summary"],
                characters=e.get("characters", []),
            ))
        for d in data.get("decisions", []):
            wiki.decisions.append(DecisionEntry(
                round=d["round"],
                type=d["type"],
                summary=d["summary"],
                alternatives=d.get("alternatives", []),
                consequences=d.get("consequences", ""),
            ))
        wiki.relationships = data.get("relationships", {})
        return wiki


# ============================================================
# 序列化辅助
# ============================================================

def wiki_to_json(wiki: CharacterWiki) -> str:
    """序列化 wiki 为 JSON 字符串"""
    import json
    return json.dumps(wiki.to_dict(), ensure_ascii=False, indent=2)


def wiki_from_json(s: str) -> CharacterWiki:
    """从 JSON 字符串反序列化"""
    import json
    return CharacterWiki.from_dict(json.loads(s))


# ============================================================
# 渲染辅助
# ============================================================

def render_wiki_summary(wiki: CharacterWiki) -> str:
    """生成 wiki 摘要（用于注入 system prompt）"""
    if not wiki.characters:
        return ""
    lines = ["## 🕸️ 人物 Wiki（仅本存档）"]
    for char in sorted(wiki.characters.values(), key=lambda c: -c.appear_count)[:10]:
        lines.append(f"### {char.id}（{char.relationship}）出现 {char.appear_count} 次")
        if char.promises_player:
            lines.append(f"  - 我方承诺：{' / '.join(char.promises_player[:3])}")
        if char.promises_npc:
            lines.append(f"  - 对方承诺：{' / '.join(char.promises_npc[:3])}")
        if char.traits:
            lines.append(f"  - 性格：{'、'.join(char.traits[:5])}")
    return "\n".join(lines)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Character Wiki Test (v1.7.1)")
    print("=" * 50)

    wiki = CharacterWiki(save_id="test-001")

    # 测试 1：手动添加
    char = wiki.add_or_update_character("张顺", round=1, summary="牙行老板", relationship="熟人")
    assert char.id == "张顺"
    assert char.appear_count == 1
    print(f"✅ test_add_character: {char.id} ({char.relationship})")

    # 测试 2：重复出现
    char2 = wiki.add_or_update_character("张顺", round=5, summary="讨价还价")
    assert char2.appear_count == 2
    assert char2.first_appear_round == 1
    assert char2.last_appear_round == 5
    print(f"✅ test_reappear: appear_count={char2.appear_count}")

    # 测试 3：自动提取 NPC
    narrative = """张顺说："三两三，不能再多了。"
你心里想：他出价真低。
丁娘子答道："代织的事包在我身上。\""""
    wiki.auto_extract_from_narrative(narrative, round=2)
    assert "张顺" in wiki.characters
    assert "丁娘子" in wiki.characters
    print(f"✅ test_auto_extract_npc: {list(wiki.characters.keys())}")

    # 测试 4：承诺提取
    assert len(wiki.characters["丁娘子"].promises_npc) >= 1
    assert any("代织" in p for p in wiki.characters["丁娘子"].promises_npc)
    print(f"✅ test_extract_promises: {wiki.characters['丁娘子'].promises_npc}")

    # 测试 5：决策
    wiki.add_decision(round=3, type="negotiate", summary="讨价还价", alternatives=["全卖", "问代织"])
    assert len(wiki.decisions) == 1
    print(f"✅ test_add_decision: {wiki.decisions[0].summary}")

    # 测试 6：序列化
    data = wiki.to_dict()
    assert "characters" in data
    assert "events" in data
    print(f"✅ test_serialize: {len(data['characters'])} chars, {len(data['events'])} events")

    # 测试 7：反序列化
    wiki2 = CharacterWiki.from_dict(data)
    assert wiki2.characters["张顺"].id == "张顺"
    print(f"✅ test_deserialize: roundtrip OK")

    # 测试 8：渲染 summary
    summary = render_wiki_summary(wiki)
    assert "张顺" in summary
    assert "丁娘子" in summary
    print(f"✅ test_render_summary: {len(summary)} chars")
    print()
    print("--- summary ---")
    print(summary)

    print("\n✅ 所有 Character Wiki 测试通过")