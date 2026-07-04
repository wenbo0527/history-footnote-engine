"""扩展insight_tree的trigger_keywords（增加同义词覆盖）

目的：让玩家用更自然的表达也能触发insight
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

# 同义词扩展（按insight id）
SYNONYM_EXPANSIONS = {
    "ins_silk_trade": ["丝绸", "织机", "买卖", "行情", "牙行",
                        "织", "绸", "盛泽", "湖绫", "丝", "机户", "缫丝", "络丝", "机织",
                        "经线", "梭子", "织造"],
    "ins_silver_tax": ["纳税", "银子", "赋税", "一条鞭", "税单",
                        "税", "银", "上供", "交税", "赋", "差役", "摊派", "加派", "加税"],
    "ins_li_jia": ["里长", "里甲", "编户", "催税", "徭役",
                    "里", "甲", "催", "差", "户籍", "人丁", "田亩"],
    "ins_city_life": ["茶馆", "集市", "闲聊", "听说", "镇上",
                       "城", "市", "苏州", "镇", "街", "巷", "庙", "会"],
    "ins_expand_ambition": ["扩大", "添织机", "雇工", "做大", "多接单",
                             "扩展", "规模", "扩张", "添机", "雇人", "发家", "兴业"],
    "ins_north_south": ["北方", "边关", "辽东", "加派", "军饷",
                        "北", "边", "辽", "军", "九边", "京师", "京城"],
    "ins_bureaucracy": ["知县", "衙门", "书吏", "官府", "告状",
                        "县", "衙", "吏", "官", "府", "官差", "师爷", "胥吏", "巡抚", "知府"],
    "ins_decline_signal": ["亡国", "衰落", "不行了", "大明朝",
                           "衰", "亡", "亡天下", "乱世", "末世", "礼崩乐坏"],
}


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))
    tree = config.get("growth", {}).get("insight_tree", [])

    expanded_count = 0
    for insight in tree:
        iid = insight["id"]
        if iid in SYNONYM_EXPANSIONS:
            old_kws = set(insight.get("trigger_keywords", []))
            new_kws = old_kws | set(SYNONYM_EXPANSIONS[iid])
            if new_kws != old_kws:
                insight["trigger_keywords"] = sorted(new_kws)
                added = len(new_kws) - len(old_kws)
                expanded_count += added
                print(f"  {iid}: {len(old_kws)}→{len(new_kws)}关键词 (+{added})")

    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ 共扩展{expanded_count}个同义词关键词")


if __name__ == "__main__":
    main()