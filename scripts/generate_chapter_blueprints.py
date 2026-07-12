"""🆕 v2.10.1 W52 P0-1: 生成 chapter 2-9 blueprints

依据 W52 优化清单 P0-1：chapter 蓝图目前只有 1 个,需补 8 个。
每个蓝图基于 chapter 1 schema(99 行)骨架生成：
- meta: act / role / emotion_tone / choice_type / suggested_node_count
- nodes: 4 个 (introduction / escalation / climax / resolution)
- differentiation: 守乡人 / 外望人 路径分化

依据 docs/design/v2.10.1-W85-涌现式章节设计.md
W85 5 阶段模板（opening / rising_conflict / crisis / convergence / resolution）
"""
import json
from pathlib import Path

OUT_DIR = Path("eras/wanli1587")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 9 个章节的主题与时间线（万历十五年1587）
CHAPTERS = [
    {
        "id": 2,
        "title": "三月初一·税单",
        "subtitle": "春风得意马蹄疾",
        "act": "departure",
        "tone": "unease",
        "choice": "whether_to_resist",
        "theme": "税单落地,咬牙抗税",
    },
    {
        "id": 3,
        "title": "三月中·告官",
        "subtitle": "府衙深似海",
        "act": "confrontation",
        "tone": "frustration",
        "choice": "whether_to_complain",
        "theme": "上告苏州府,无门",
    },
    {
        "id": 4,
        "title": "四月初·春蚕",
        "subtitle": "满城尽带黄金甲",
        "act": "pressure",
        "tone": "strain",
        "choice": "whether_to_give_up",
        "theme": "春蚕上簇,咬牙撑",
    },
    {
        "id": 5,
        "title": "四月中·织机",
        "subtitle": "织梭声中夜未央",
        "act": "grinding",
        "tone": "exhaustion",
        "choice": "whether_to_rest",
        "theme": "织机损坏,换还是修",
    },
    {
        "id": 6,
        "title": "五月·债台",
        "subtitle": "屋漏偏逢连夜雨",
        "act": "crisis",
        "tone": "despair",
        "choice": "whether_to_borrow",
        "theme": "债务如山,找人借",
    },
    {
        "id": 7,
        "title": "六月·倭警",
        "subtitle": "海疆不靖人心慌",
        "act": "external_threat",
        "tone": "fear",
        "choice": "whether_to_flee",
        "theme": "倭寇来袭,躲还是守",
    },
    {
        "id": 8,
        "title": "七月·内讧",
        "subtitle": "人心离散各自飞",
        "act": "betrayal",
        "tone": "shock",
        "choice": "whether_to_forgive",
        "theme": "邻人背叛,怒还是恕",
    },
    {
        "id": 9,
        "title": "八月中秋·团圆",
        "subtitle": "月明千里寄相思",
        "act": "rest",
        "tone": "tenderness",
        "choice": "whether_to_renovate",
        "theme": "中秋夜,家人共",
    },
]

# 4 个 node 模板
NODE_TEMPLATE = [
    {
        "role": "introduction",
        "completion": "round_4_reached",
    },
    {
        "role": "escalation",
        "completion": "round_8_reached",
    },
    {
        "role": "climax",
        "completion": "round_12_reached",
    },
    {
        "role": "resolution",
        "completion": "round_16_reached",
    },
]

# NPC ids (从 chapter 1 引用,后续章节复用)
NPC_IDS = ["fm_wife", "fm_son", "npc_zhao_lizhang", "npc_wang_sao"]


def make_nodes(chapter_id: int, theme: str) -> list[dict]:
    """生成 4 个 node,主题驱动场景描述"""
    scenes = [
        f"【{theme}】场景开篇。家庭/邻人对话引入本章主题。",
        f"【{theme}】外部压力升级。衙役/债主/倭寇到访。",
        f"【{theme}】高潮抉择。玩家被迫表态,不可回避。",
        f"【{theme}】本回合收束,留悬念到下章。",
    ]
    nodes = []
    for i, (tmpl, scene) in enumerate(zip(NODE_TEMPLATE, scenes), 1):
        nodes.append({
            "index": i,
            "role": tmpl["role"],
            "scene": scene,
            "npc_ids": NPC_IDS,
            "option_directions": [
                {"text": "顺从,认命", "path_hint": "main_tax_resistance"},
                {"text": "硬抗,不理", "path_hint": "main_tax_resistance"},
                {"text": "求援,找人", "path_hint": "side_silk_trade"},
                {"text": "逃避,躲藏", "path_hint": "side_silk_trade"},
            ],
            "knowledge_ids": [f"kn_ch{chapter_id}_node{i}"],
            "completion_condition": tmpl["completion"],
        })
    return nodes


def make_blueprint(ch: dict) -> dict:
    """生成单个 chapter 蓝图"""
    return {
        "chapter_id": ch["id"],
        "chapter_title": ch["title"],
        "chapter_subtitle": ch["subtitle"],
        "meta": {
            "act": ch["act"],
            "role": "ordinary",
            "emotion_tone": ch["tone"],
            "choice_type": ch["choice"],
            "suggested_node_count": 4,
            "suggested_template": "pressure_divide_choose_consequence",
        },
        "transition_hint": "season",
        "nodes": make_nodes(ch["id"], ch["theme"]),
        "differentiation": {
            "_description": "Build × 节点分化（v2.8.0 段四）：同 seed 不同 Build 体验不同",
            "守乡人": {
                "_note": f"守乡人 path 中第 {ch['id']} 章专属场景：聚焦家庭与守土"
            },
            "外望人": {
                "_note": f"外望人 path 中第 {ch['id']} 章专属场景：聚焦外出与商机"
            },
        },
    }


def main():
    """生成 8 个 chapter 蓝图"""
    for ch in CHAPTERS:
        bp = make_blueprint(ch)
        out_path = OUT_DIR / f"chapter{ch['id']}_blueprint.json"
        out_path.write_text(
            json.dumps(bp, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"✓ chapter{ch['id']}_blueprint.json: {len(out_path.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
