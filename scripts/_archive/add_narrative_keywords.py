"""为narrative_guided类型的insight添加trigger_keywords作为后备触发"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

# 给narrative_guided的insight加trigger_keywords（用于内容匹配）
NARRATIVE_KEYWORDS = {
    "ins_silver_economy": ["白银", "银子", "番银", "海外", "流通", "进口", "银矿"],
    "ins_moral_vs_reality": ["规矩", "逃税", "道德", "吃亏", "礼法", "违规", "本分", "偷税", "灰色"],
    "ins_tribute_trap": ["上供", "丝绸", "进贡", "朝廷", "算账", "成本", "利润", "给朝廷"],
    "ins_no_escape": ["逃", "躲", "出路", "难", "无路", "困局", "无处可逃", "走投无路"],
    "ins_bigger_not_better": ["扩张", "做大", "雇工", "机户", "下场", "亏", "代价", "得不偿失"],
    "ins_grand_failure": ["衰落", "失败", "亡国", "末世", "完了", "完了完了", "大势已去", "回天乏术"],
}


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))
    tree = config.get("growth", {}).get("insight_tree", [])

    for insight in tree:
        iid = insight["id"]
        if iid in NARRATIVE_KEYWORDS:
            existing = insight.get("trigger_keywords", [])
            new = sorted(set(existing) | set(NARRATIVE_KEYWORDS[iid]))
            insight["trigger_keywords"] = new
            print(f"  {iid}: +{len(NARRATIVE_KEYWORDS[iid])}关键词 → {new}")

    ERA_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n✅ 完成")


if __name__ == "__main__":
    main()