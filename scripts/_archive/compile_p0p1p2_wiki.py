"""写入v3.0 P0 + v4.0 P1 + v5.0 P2 共9条支线的精简Wiki

设计原则：
- entries: 严格<200字符/条
- snippets: <200字符/条
- 不新增identity（避免CLI爆炸）

v3.0 P0（3条）：织工路线、出家/山人、抗税/反抗
v4.0 P1（3条）：手艺转行、入幕/师爷、匠官
v5.0 P2（3条）：流民/乞丐、医药、戏曲/说书
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")


# === v3.0 P0：3条支线entries ===

V3_ENTRIES = [
    {
        "id": "sc_weaver_fall",
        "layer": "scene",
        "title": "织工路线：从机户到机工",
        "content": "经营失败→卖掉织机→变成机工。阶段：挣扎期（借高利贷）→卖机期（最后5-10两）→机工期（丝市等活日薪3-4分）→觉醒期（接触集体行动）。机工'朝不谋夕，得业则生，失业则死'。约60%挣扎期机户最终滑落。",
        "trigger_keywords": ["织工", "机工", "丝市", "卖机", "失业", "雇工"],
        "trigger_scene": ["盛泽市集"],
        "related_entries": ["sc_tax_card"],
        "source_refs": "曹时聘奏报；葛成传",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_taxes_keen",
        "layer": "scene",
        "title": "万历矿税之祸",
        "content": "万历二十四年（1596）起派出宦官任矿监税使，绕过官僚系统直接搜刮。孙隆在苏州设20多个税卡：每台织机三钱，每匹布五分。对3台织机小户，加税后约1.2-1.4两/月（占月收入40-47%）。葛成起义：万历二十九年（1601），机工聚众打死税棍，迫使税卡撤销。",
        "trigger_keywords": ["税监", "矿税", "孙隆", "税卡", "黄建节", "葛成"],
        "trigger_scene": ["县衙", "自家作坊"],
        "related_entries": ["pr_silver_inflow"],
        "source_refs": "曹时聘奏报；陈继儒《吴葛将军墓碑》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_monks_laymen",
        "layer": "scene",
        "title": "出家/山人路线",
        "content": "出家硬约束：度牒（需数两）+寺院接收+1年考察+戒律。女性几乎不可能（建文三年法令：59岁以下不许为尼，违者杖一百还俗入官为奴；万历三十三年按猪肉价卖给光棍）。替代路径：居士/带发修行/山人。陈继儒1587年'取儒衣冠焚弃之'，隐居东佘山。",
        "trigger_keywords": ["出家", "度牒", "山人", "陈继儒", "寺庙", "灵岩寺", "居士"],
        "trigger_scene": ["自家作坊"],
        "related_entries": ["sc_imperial_exam_path"],
        "source_refs": "明代佛教研究；陈继儒传记",
        "confidence": "high",
        "needs_review": False,
    },
]


# === v4.0 P1：3条支线entries ===

V4_ENTRIES = [
    {
        "id": "sc_craft_pivot",
        "layer": "scene",
        "title": "手艺转行路线",
        "content": "织户可转：染色（入门3-5两，月入1.5-2两）、刺绣（1-2两，月入1-3两，'顾绣'有品牌溢价）、踹布（几乎零成本，月入0.8-1两，体力活）、开染坊（15-25两投入，月入3-5两）。女性优势方向是刺绣（顾名世之妾韩希孟创'顾绣'）。",
        "trigger_keywords": ["染色", "刺绣", "踹布", "顾绣", "转行", "染坊"],
        "trigger_scene": ["自家作坊"],
        "related_entries": ["sc_weaver_fall"],
        "source_refs": "明代丝织业研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_muye_shiye",
        "layer": "scene",
        "title": "入幕/师爷路线",
        "content": "入幕：当官员私人幕僚，处理刑名/钱谷/文书。月入2-5两。师爷：替人写诉状/打官司，按件收费。要求：识字+懂律法+会处事。常见路径：科举落榜秀才/告老官员幕僚/被大官赏识。入幕风险：被当替罪羊、卷入党争、名声受损（'幕僚'社会地位低）。",
        "trigger_keywords": ["入幕", "幕僚", "师爷", "幕友", "刑名", "钱谷"],
        "trigger_scene": ["县衙"],
        "related_entries": ["sc_imperial_exam_path"],
        "source_refs": "明代幕僚研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_jiang_guan",
        "layer": "scene",
        "title": "匠官路线：手艺入仕",
        "content": "明代设'工部'，有少量'匠官'名额（营缮所/文思院等）。匠人可凭技术入仕：从'匠籍'经考核升迁。现实：名额极少、晋升慢、社会地位低。万历年间'匠户'实际地位：介于民户与军户之间。多数匠人终身为匠，子孙承袭。",
        "trigger_keywords": ["匠官", "工部", "匠籍", "营缮所", "文思院"],
        "trigger_scene": [],
        "related_entries": ["sc_craft_pivot"],
        "source_refs": "明代匠户制度研究",
        "confidence": "medium",
        "needs_review": True,
    },
]


# === v5.0 P2：3条支线entries ===

V5_ENTRIES = [
    {
        "id": "sc_beggars",
        "layer": "scene",
        "title": "流民/乞丐路线",
        "content": "万历年间流民已是常态：失去土地/破产/灾荒逃荒者。乞丐群体有'丐帮'雏形，分地盘（盛泽/苏州各有势力）。求生方式：乞讨/拾荒/偷盗/卖艺/给寺庙做苦力。女性沦为'乞丐婆'或被卖入青楼。风险：被收容所抓去服苦役、饥寒致死。",
        "trigger_keywords": ["乞丐", "流民", "乞讨", "丐帮", "逃荒"],
        "trigger_scene": [],
        "related_entries": ["sc_weaver_fall"],
        "source_refs": "明代流民研究",
        "confidence": "medium",
        "needs_review": False,
    },
    {
        "id": "sc_medicine",
        "layer": "scene",
        "title": "医药/悬壶济世",
        "content": "明代医生分：太医院（御医）/ 官医（惠民药局）/ 坐堂医（药铺）/ 走方医（铃医）/ 女医（稳婆/治女科）。铃医走街串巷摇铃招客，卖药兼看病。名医如李时珍《本草纲目》1578年成书。学习途径：家传/拜师/自学医书。女医主要看女科和接生。",
        "trigger_keywords": ["医药", "医生", "铃医", "走方医", "本草纲目", "惠民药局"],
        "trigger_scene": ["盛泽市集"],
        "related_entries": [],
        "source_refs": "明代医学史",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_opera_storyteller",
        "layer": "scene",
        "title": "戏曲/说书路线",
        "content": "万历年间昆曲兴起（魏良辅改良昆山腔），苏州/盛泽有戏班。说书人活跃于茶馆/庙会/私宅。收入：戏班演员月入1-3两（名角可达5两+）；说书按场收费，每场50-200文。女性艺人罕见但存在（如女伶/歌妓）。社会地位：'戏子'社会评价低，但收入可观。",
        "trigger_keywords": ["昆曲", "戏班", "说书", "魏良辅", "戏子", "女伶"],
        "trigger_scene": ["茶馆", "自家作坊"],
        "related_entries": [],
        "source_refs": "明代戏曲史",
        "confidence": "medium",
        "needs_review": False,
    },
]


# === 共用snippets（精选4条最有故事性的） ===

NEW_SNIPPETS = [
    {
        "id": "sn_cao_shit聘",
        "source": "曹时聘奏报（明实录）",
        "applies_to_scenes": ["自家作坊", "盛泽市集"],
        "trigger_keywords": ["机工", "失业", "卖机", "织工"],
        "npc_use_case": "DM描述机工处境时引用",
        "snippet_text": "吴民生齿最繁，恒产绝少……浮食寄民，朝不谋夕，得业则生，失业则死。",
        "target_gender": "all",
    },
    {
        "id": "sn_ge_cheng_story",
        "source": "陈继儒《吴葛将军墓碑》",
        "applies_to_scenes": ["自家作坊", "县衙"],
        "trigger_keywords": ["葛成", "反抗", "税监", "起义"],
        "npc_use_case": "NPC讲反抗故事——'葛成是真汉子'",
        "snippet_text": "葛成在玄妙观聚众，万余织工响应，'不伤无辜，不取金银'，只针对税吏。事后主动投案，被判死刑后改判，狱中13年。苏州人称他为'葛贤''葛将军'。",
        "target_gender": "male",
    },
    {
        "id": "sn_chen_jiru_1587",
        "source": "陈继儒传记（1587年）",
        "applies_to_scenes": ["茶馆", "自家作坊"],
        "trigger_keywords": ["山人", "陈继儒", "隐居", "眉公"],
        "npc_use_case": "NPC羡慕山人生活——'看人家眉公先生'",
        "snippet_text": "二十九岁，陈继儒'取儒衣冠焚弃之'，隐居东佘山，以编书写画自娱。靠卖字画（一幅0.5-2两）、编书刻书为生，活得比当官的还自在。",
        "target_gender": "all",
    },
    {
        "id": "sn_nun_59_law",
        "source": "《大明律》及万历三十三年法令",
        "applies_to_scenes": ["自家作坊"],
        "trigger_keywords": ["出家", "尼姑", "女尼", "度牒"],
        "npc_use_case": "女性玩家想出家时DM提示",
        "snippet_text": "建文三年令：未满59岁不许为尼，违者杖一百还俗入官为奴。万历三十三年更严：按猪肉价卖给光棍。女性出家是硬约束——只能做居士或山人。",
        "target_gender": "female",
    },
]


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    # 1. 追加entries
    existing_entry_ids = {e["id"] for e in config["knowledge"]["entries"]}
    added_entries = 0
    for entry in V3_ENTRIES + V4_ENTRIES + V5_ENTRIES:
        if entry["id"] not in existing_entry_ids:
            config["knowledge"]["entries"].append(entry)
            added_entries += 1

    # 2. 追加snippets
    existing_snip_ids = {s["id"] for s in config["knowledge"]["narrative_snippets"]}
    added_snippets = 0
    for snip in NEW_SNIPPETS:
        if snip["id"] not in existing_snip_ids:
            config["knowledge"]["narrative_snippets"].append(snip)
            added_snippets += 1

    # 3. 写回
    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 统计
    total_entries = len(config["knowledge"]["entries"])
    total_snippets = len(config["knowledge"]["narrative_snippets"])
    era_size = len(json.dumps(config, ensure_ascii=False))

    print(f"✅ 添加entries: {added_entries}条（v3.0={len(V3_ENTRIES)}, v4.0={len(V4_ENTRIES)}, v5.0={len(V5_ENTRIES)}）")
    print(f"✅ 添加snippets: {added_snippets}条")
    print(f"📊 当前 totals: entries={total_entries}, snippets={total_snippets}")
    print(f"📊 era.json大小: {era_size} 字符 (~{era_size // 1024}KB)")


if __name__ == "__main__":
    main()