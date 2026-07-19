"""给 era.json 加 v1.4.0 新字段：pacing_anchors, failure_mappings, cognitive_frames, voices"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

data = json.loads(ERA_PATH.read_text(encoding="utf-8"))
world = data.setdefault("world", {})

# ============================================================
# pacing_anchors — 节奏锚点（v1.4.0+）
# ============================================================
pacing_anchors = [
    {
        "id": "anchor_spring_tax",
        "trigger_round": 3,
        "foreshadow_round": 1,
        "trigger_date": "1587年2月",
        "description": "春税征收",
        "time_mode": "now_time",
        "foreshadowing_lead": "镇上在传今年春税的数额",
        "dm_instruction": "用里长上门通知的形式推进；给玩家'该交多少'的取舍",
    },
    {
        "id": "anchor_jap_pirates_news",
        "trigger_round": 8,
        "foreshadow_round": 6,
        "trigger_date": "1587年5月",
        "description": "月港方向倭寇警报",
        "time_mode": "sharp_cut",
        "foreshadowing_lead": "茶馆里有客商说福建那边不太平",
        "dm_instruction": "锐切：镇外河上飘来一具浮尸，旁边压着倭字木板。立刻把时代危机感推到玩家面前。",
    },
    {
        "id": "anchor_silk_market_collapse",
        "trigger_round": 15,
        "foreshadow_round": 12,
        "trigger_date": "1587年9月",
        "description": "丝价大跌",
        "time_mode": "sharp_cut",
        "foreshadowing_lead": "牙行说外地客商最近少了很多",
        "dm_instruction": "锐切：王掌柜沉着脸告诉你——昨日杭州客官退了三批货。丝价一夜跌了三成。",
    },
    {
        "id": "anchor_emperor_illness_rumor",
        "trigger_round": 22,
        "foreshadow_round": 19,
        "trigger_date": "1588年4月",
        "description": "京师传皇帝抱恙",
        "time_mode": "now_time",
        "foreshadowing_lead": "县衙贴告示时有人偷偷议论",
        "dm_instruction": "用谣言方式呈现，给玩家'大人物倒了，下面会怎样'的紧张感",
    },
    {
        "id": "anchor_mining_tax_eunuch",
        "trigger_round": 30,
        "foreshadow_round": 27,
        "trigger_date": "1588年12月",
        "description": "矿监到苏州",
        "time_mode": "sharp_cut",
        "foreshadowing_lead": "苏州城里来了一批生面孔的差役",
        "dm_instruction": "锐切：矿监的轿子从苏州城方向来盛泽镇了。一时鸡飞狗跳。",
    },
    {
        "id": "anchor_imperial_exam_announcement",
        "trigger_round": 25,
        "foreshadow_round": 23,
        "trigger_date": "1588年7月",
        "description": "科举乡试报名",
        "time_mode": "slow_time",
        "foreshadowing_lead": "镇上李秀才在茶馆里说今年的乡试",
        "dm_instruction": "慢时间：玩家若有科举意向，深入展开内心挣扎（读书人的本分 vs 现实压力）",
    },
]
world["pacing_anchors"] = pacing_anchors

# ============================================================
# failure_mappings — 失败叙事化
# ============================================================
world["failure_mappings"] = {
    "action": "你做不到 A，但发现 B 的可能——比如：织不出花绫，但意外发现桑叶里混了一种能染藕色的野草",
    "persuasion": "对方没同意，但无意中透露了关键信息——比如：王掌柜不卖丝给你，但告诉你'杭州客官最近全撤了'",
    "exploration": "找不到目标，但翻到了意料之外的东西——比如：账房没找到，但翻到了一本万历十年的旧户籍册",
    "choice": "你以为会怎样，实际却更复杂——比如：交了税，但发现邻居没交，催税的反而对你另眼相看",
    "silk_weaving": "织机突然崩了一根经线——但你由此发现邻家有更便宜的新机",
    "tax_pay": "交了税却没收到收据——被里长私吞了一钱；下月催税还得再交",
    "borrowing_money": "借了高利贷，但月利是四分不是三分——债务雪球越滚越大",
    "journey": "没走到苏州——路上桥断了，绕道多花两天；意外发现一条走私的小路",
}

# ============================================================
# cognitive_frames — 认知框架锁定
# ============================================================
world["cognitive_frames"] = {
    "imperial_exam": {
        "frame_id": "imperial_exam",
        "highlight": [
            "科举消息（乡试/会试/府学动态）",
            "文人圈动态（李秀才/书肆/经义讨论）",
            "士绅家宴/书院讲学",
            "朝廷党争与士人立场",
            "经史典故引用",
        ],
        "suppress": [
            "丝价行情波动",
            "织工工资/雇工成本",
            "桑叶/蚕种价格",
            "牙行八卦",
            "市集日常",
        ],
    },
    "business": {
        "frame_id": "business",
        "highlight": [
            "丝价波动",
            "客商动向（杭州/苏州/福建）",
            "牙行议价",
            "高利贷与当铺",
            "市集行情",
            "行会与商帮",
        ],
        "suppress": [
            "科举消息",
            "文人雅集",
            "经义讨论",
            "士绅家宴",
            "朝廷政令细节",
        ],
    },
    "monk": {
        "frame_id": "monk",
        "highlight": [
            "佛寺/僧侣",
            "因果/轮回说",
            "简朴生活",
            "出家仪式",
            "世事无常的感悟",
        ],
        "suppress": [
            "科举功名",
            "商场经营",
            "政治党争",
        ],
    },
    "tax_resist": {
        "frame_id": "tax_resist",
        "highlight": [
            "税吏的压迫",
            "其他织户的不满",
            "朝廷加派的传闻",
            "里长的刁难",
            "抗税的代价（逃户/抓壮丁）",
        ],
        "suppress": [
            "科举功名",
            "商业机会",
        ],
    },
    "weaving": {
        "frame_id": "weaving",
        "highlight": [
            "织机/经线/梭子",
            "丝价行情",
            "牙行交易",
            "桑田/蚕事",
            "水脚银/丝税",
        ],
        "suppress": [
            "科举消息",
            "经义讨论",
        ],
    },
}

# ============================================================
# voices — 内在声音（DE 风格的「脑海中的声音」）
# ============================================================
world["voices"] = [
    {
        "id": "voice_accountant",
        "name": "算盘声",
        "trigger": "always",
        "prompt_fragment": "一个声音在你脑子里拨算盘：今天收入几分、支出几分，月底还能剩多少。这个声音不会停。",
    },
    {
        "id": "voice_moral",
        "name": "读书人的本分",
        "trigger": "moral_anxiety>3",
        "prompt_fragment": "你想起先生的话：'君子喻于义，小人喻于利'。但先生自己也没饭吃。",
    },
    {
        "id": "voice_road",
        "name": "远方的路",
        "trigger": "north_threat>2",
        "prompt_fragment": "你想起老家听来的话：北边不太平。是不是该想想后路？",
    },
    {
        "id": "voice_safety",
        "name": "活下去",
        "trigger": "tax_burden>5 OR silver_pressure>3",
        "prompt_fragment": "一个声音反复说：先活下去。银子比脸重要，粮食比道理重要。",
    },
    {
        "id": "voice_mother",
        "name": "老娘的咳喘",
        "trigger": "livelihood<5",
        "prompt_fragment": "你想起老娘临走时的话：'娃啊，别让阿宝饿着'。嗓子里又有点发酸。",
    },
    {
        "id": "voice_dignity",
        "name": "做人要有骨气",
        "trigger": "moral_anxiety>4",
        "prompt_fragment": "你想起爹临终前说的：'咱家虽然穷，但不能让人指着脊梁骨'。",
    },
]

# 写回
ERA_PATH.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"✅ era.json updated:")
print(f"  pacing_anchors: {len(pacing_anchors)} 个史实锚点")
print(f"  failure_mappings: {len(world['failure_mappings'])} 种失败转化")
print(f"  cognitive_frames: {len(world['cognitive_frames'])} 个路线框架")
print(f"  voices: {len(world['voices'])} 个内在声音")
