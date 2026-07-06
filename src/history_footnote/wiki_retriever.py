"""🆕 v1.7.37 Wiki Retriever（按需检索）

设计：
- Wiki 内容在 docs/eras/万历十五年/*.md
- LLM 调用工具 search_wiki() 按关键词/意图/场景检索
- 返回 top-N 片段（带 score）
- 支持 4 类内容：
  - 城市Wiki（4 城市感官/功能/差异）
  - 离乡路线Wiki（100+ 路线片段）
  - 闲谈素材Wiki（30+ 故事片段）
  - 支线路径Wiki（路径+岔路）

依据用户洞察：
> Wiki 内容是按需注入的，由 LLM 处理

不是全量塞 prompt，而是 LLM 主动调用工具检索。
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============= 文档加载 =============

WIKI_DIRS = {
    "city": Path("docs/eras/万历十五年/城市Wiki.md"),
    "route": Path("docs/eras/万历十五年/离乡路线Wiki.md"),
    "gossip": Path("docs/eras/万历十五年/闲谈素材Wiki.md"),
    "branch": Path("docs/eras/万历十五年/支线路径Wiki.md"),
}


@dataclass
class WikiFragment:
    """Wiki 片段（带元数据）"""
    id: str
    title: str
    content: str
    source_file: str
    category: str  # city/route/gossip/branch
    section: str  # 城市/感官层/功能层/...
    city: str  # 苏州/杭州/盛泽/...
    keywords: list = field(default_factory=list)
    score: float = 0.0


def load_all_wikis() -> dict[str, str]:
    """加载所有 Wiki 文档（content + path）"""
    out = {}
    for cat, path in WIKI_DIRS.items():
        if path.exists():
            out[cat] = path.read_text(encoding="utf-8")
    return out


# ============= 文档分片 =============

CITY_KEYWORDS = {
    "suzhou": ["苏州", "阊门", "山塘", "观前", "玄妙观", "太监弄", "织造", "金阊门", "丝织"],
    "hangzhou": ["杭州", "西湖", "清河坊", "武林", "钱塘"],
    "songjiang": ["松江", "枫桥", "上海", "棉布"],
    "nanjing": ["南京", "应天", "京城", "贡院", "秦淮"],
    "shengze": ["盛泽", "织户", "家庭作坊"],
}


def detect_city(text: str) -> str:
    """从文本检测城市（返回 city_id）"""
    text_lower = text.lower()
    for city, kws in CITY_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                return city
    return ""


def split_into_fragments(content: str, source_file: str, category: str) -> list[WikiFragment]:
    """把 Wiki 文档拆分成片段"""
    fragments = []
    # 按二级标题（## 段落）分片
    pattern = r"^## (.+?)$"
    lines = content.split("\n")
    current_title = ""
    current_section = ""
    current_content = []
    city = detect_city(content[:500])  # 默认城市（前 500 字符）

    def flush():
        if current_content and current_title:
            text = "\n".join(current_content).strip()
            if len(text) > 50:  # 至少 50 字符
                f_city = detect_city(text) or city
                f = WikiFragment(
                    id=f"{category}_{current_title[:20]}",
                    title=current_title,
                    content=text,
                    source_file=source_file,
                    category=category,
                    section=current_section,
                    city=f_city,
                )
                fragments.append(f)
        current_content.clear()

    for line in lines:
        if re.match(r"^## ", line):
            # 新段落
            flush()
            current_title = line.replace("## ", "").strip()
            current_section = "main"
        elif re.match(r"^### ", line):
            # 三级标题：作为"section"
            flush()
            current_section = line.replace("### ", "").strip()
            current_title = current_section
        elif re.match(r"^# ", line):
            # 一级标题
            flush()
            current_title = line.replace("# ", "").strip()
            current_section = "header"
        else:
            current_content.append(line)
    flush()
    return fragments


# ============= 检索 =============

# 关键词 → 类别权重
INTENT_WEIGHTS = {
    "city": {
        # 城市感官/功能
        "到达": 1.5, "码头": 1.3, "街": 1.2, "景象": 1.3, "感觉": 1.2,
        "感官": 1.5, "声音": 1.2, "气味": 1.2, "人群": 1.2,
        "卖": 1.0, "买": 1.0, "吃": 1.1, "看": 1.0,
        "阊门": 1.5, "西湖": 1.5, "观前": 1.4, "山塘": 1.4,
    },
    "route": {
        "去": 1.5, "到": 1.3, "航行": 1.5, "船": 1.3, "走": 1.2,
        "运河": 1.4, "路": 1.3, "码头": 1.2, "城": 1.2,
        "杭州": 1.5, "苏州": 1.4, "盛泽": 1.4, "松江": 1.4, "南京": 1.4,
        "临清": 1.5, "济宁": 1.5, "扬州": 1.5,
    },
    "gossip": {
        "闲谈": 1.5, "故事": 1.4, "传闻": 1.3, "听说": 1.2, "知道": 1.0,
        "卖": 1.0, "买": 1.0, "织": 1.2, "绸": 1.2,
        "施润泽": 1.5, "蒋兴哥": 1.5, "杨八老": 1.5, "金瓶梅": 1.4,
        "三言": 1.4, "二拍": 1.4, "盛泽": 1.3, "牙行": 1.2,
    },
    "branch": {
        "路径": 1.5, "岔路": 1.5, "选择": 1.3, "走": 1.2,
        "回": 1.0, "进": 1.0, "去": 1.0,
    },
}


def score_fragment(fragment: WikiFragment, query: str, intent: str = "") -> float:
    """给片段打分"""
    score = 0.0
    query_lower = query.lower()
    content_lower = fragment.content.lower()
    title_lower = fragment.title.lower()

    # 1. 关键词命中（content）
    query_words = set(query_lower.split())
    content_words = set(content_lower.split())
    common = query_words & content_words
    score += len(common) * 1.0
    # 短语匹配
    if query_lower in content_lower:
        score += 3.0
    if query_lower in title_lower:
        score += 2.0

    # 2. 类别权重
    cat_weights = INTENT_WEIGHTS.get(fragment.category, {})
    for word in query_words:
        if word in cat_weights:
            score += cat_weights[word] * 0.5

    # 3. 城市匹配（如果有 city 参数）
    # 4. intent 类别 boost
    if intent and intent == fragment.category:
        score += 1.0

    # 5. 长度归一（避免过长片段占优）
    if len(fragment.content) > 1500:
        score *= 0.7
    elif len(fragment.content) < 200:
        score *= 0.5

    return score


class WikiRetriever:
    """Wiki 检索器（按需）"""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(".")
        self._fragments: list[WikiFragment] = []
        self._loaded = False

    def load(self) -> None:
        """加载并索引所有 Wiki"""
        if self._loaded:
            return
        for cat, path in WIKI_DIRS.items():
            full_path = self.root_dir / path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                fragments = split_into_fragments(content, str(path), cat)
                self._fragments.extend(fragments)
        self._loaded = True

    def search(self, query: str, intent: str = "", city: str = "",
               category: str = "", top_k: int = 3) -> list[WikiFragment]:
        """按 query 检索片段

        Args:
            query: 检索词（玩家输入 + LLM 推理的关键词）
            intent: 意图分类（city/route/gossip/branch）
            city: 城市过滤（suzhou/hangzhou/...）
            category: 类别过滤
            top_k: 返回几个片段

        Returns:
            排序后的片段列表
        """
        if not self._loaded:
            self.load()
        scored = []
        for f in self._fragments:
            # 过滤
            if category and f.category != category:
                continue
            if city and f.city != city:
                continue
            score = score_fragment(f, query, intent)
            f.score = score
            if score > 0:
                scored.append(f)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def search_by_action(self, action_verb: str, target: str = "",
                         city: str = "", top_k: int = 3) -> list[WikiFragment]:
        """按玩家动作意图检索

        例:
            search_by_action("TRAVEL", "suzhou") → 找苏州的航行/到达/城市片段
            search_by_action("SELL", "", "shengze") → 找盛泽卖绸的闲谈/触发器
        """
        if not self._loaded:
            self.load()
        # 构造 query
        verb_intent = {
            "TRAVEL": "route",
            "MEET": "gossip",
            "SELL": "gossip",
            "BUY": "gossip",
            "CRAFT": "gossip",
            "IDLE": "gossip",
        }
        intent = verb_intent.get(action_verb, "")
        # 构造 query
        if target:
            query = f"{action_verb} {target}"
        else:
            query = action_verb
        return self.search(query, intent=intent, city=city, top_k=top_k)

    def get_stats(self) -> dict:
        """统计"""
        if not self._loaded:
            self.load()
        by_cat = defaultdict(int)
        by_city = defaultdict(int)
        for f in self._fragments:
            by_cat[f.category] += 1
            by_city[f.city or "未分类"] += 1
        return {
            "total_fragments": len(self._fragments),
            "by_category": dict(by_cat),
            "by_city": dict(by_city),
        }


# ============= 全局单例 =============

_GLOBAL_RETRIEVER: Optional[WikiRetriever] = None


def get_wiki_retriever(root_dir: Optional[Path] = None) -> WikiRetriever:
    """获取全局 Wiki 检索器"""
    global _GLOBAL_RETRIEVER
    if _GLOBAL_RETRIEVER is None:
        _GLOBAL_RETRIEVER = WikiRetriever(root_dir or Path("."))
    return _GLOBAL_RETRIEVER


def reset_wiki_retriever() -> None:
    global _GLOBAL_RETRIEVER
    _GLOBAL_RETRIEVER = None


# ============= 烟雾测试 =============

if __name__ == "__main__":
    r = WikiRetriever(Path("."))
    r.load()
    print(f"加载 {len(r._fragments)} 个片段")
    stats = r.get_stats()
    print(f"统计: {stats}")

    # 测试 1：玩家去苏州
    print("\n=== 玩家去苏州 ===")
    frags = r.search("搭船去苏州", intent="route", city="suzhou", top_k=3)
    for f in frags:
        print(f"  [{f.score:.1f}] {f.title} ({f.category}/{f.city})")
        print(f"    {f.content[:200]}...")

    # 测试 2：玩家去卖绸
    print("\n=== 玩家去卖绸（盛泽）===")
    frags = r.search_by_action("SELL", city="shengze")
    for f in frags:
        print(f"  [{f.score:.1f}] {f.title} ({f.category}/{f.city})")
        print(f"    {f.content[:200]}...")

    # 测试 3：玩家想听闲谈
    print("\n=== 玩家想听闲谈 ===")
    frags = r.search("听说施润泽的故事", intent="gossip", top_k=3)
    for f in frags:
        print(f"  [{f.score:.1f}] {f.title} ({f.category}/{f.city})")
        print(f"    {f.content[:200]}...")

    # 测试 4：杭州离乡
    print("\n=== 杭州离乡 ===")
    frags = r.search_by_action("TRAVEL", "hangzhou")
    for f in frags:
        print(f"  [{f.score:.1f}] {f.title} ({f.category}/{f.city})")
        print(f"    {f.content[:200]}...")
