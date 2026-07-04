"""在era.json里添加random_events字段

每条event:
- trigger_condition: 触发场景/回合/状态
- probability: 触发概率（0-1）
- outcomes: 加权事件列表（每个outcome有type+content）
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

RANDOM_EVENTS = [
    # === 盛泽市集场景 ===
    {
        "id": "re_market_encounter",
        "trigger_condition": {
            "scene": "盛泽市集",
            "min_round": 3,
        },
        "probability": 0.35,  # 35%触发
        "outcomes": [
            {
                "type": "npc_encounter",
                "npc_id": "npc_old_merchant",
                "weight": 3,
                "description": "你遇见一位老商人，正向路人打听今年的丝价",
                "hint": "老商人看起来消息灵通",
            },
            {
                "type": "npc_encounter",
                "npc_id": "npc_missing_child",
                "weight": 2,
                "description": "一个女人抱着孩子在哭，说孩子走失了",
                "hint": "妇人哭得很伤心",
            },
            {
                "type": "weather",
                "outcome_id": "rain_starts",
                "weight": 1,
                "description": "天空突然阴沉下来，细雨开始飘落",
                "hint": "雨不算大，但街上的小贩开始收摊",
            },
            {
                "type": "market_news",
                "outcome_id": "silk_price_rumor",
                "weight": 2,
                "description": "你听到牙人在讨论'今年第一批洋船要来了，丝价怕是要涨'",
                "hint": "这条消息对你很重要",
            },
        ],
    },
    # === 茶馆场景 ===
    {
        "id": "re_teahouse_gossip",
        "trigger_condition": {
            "scene": "茶馆",
            "min_round": 5,
        },
        "probability": 0.5,  # 50%触发
        "outcomes": [
            {
                "type": "rumor",
                "outcome_id": "fanjin_zhongju",
                "weight": 2,
                "description": "有人在聊范进中举的笑话",
                "hint": "'考了二十多次，五十四岁才中举'",
            },
            {
                "type": "rumor",
                "outcome_id": "shen_wansan_warning",
                "weight": 2,
                "description": "老者在劝年轻人不要做大——'你忘了沈万三？'",
                "hint": "做大做强不是没有风险",
            },
            {
                "type": "npc_encounter",
                "npc_id": "npc_lai_li_tou",
                "weight": 2,
                "description": "镇上'消息灵通'的癞痢头阿福晃了进来",
                "hint": "这人整天在市井晃荡，什么都知道一点",
            },
            {
                "type": "rumor",
                "outcome_id": "yuegang_news",
                "weight": 1,
                "description": "有行商在聊月港见闻——'那边一匹湖绫能卖三两'",
                "hint": "远方来的消息",
            },
        ],
    },
    # === 牙行场景 ===
    {
        "id": "re_yahang_negotiation",
        "trigger_condition": {
            "scene": "牙行",
        },
        "probability": 0.4,  # 40%触发（每次去牙行都有谈判可能）
        "outcomes": [
            {
                "type": "npc_action",
                "outcome_id": "yahang_cheat_attempt",
                "weight": 2,
                "description": "牙人似乎在成色上压价",
                "hint": "你隐约觉得他说的价低于市面",
                "requires_dice": True,
                "dice": "d20",
                "dc": 12,
                "success": "你识破了他的小动作，他反而夸你眼力好",
                "fail": "他成功压了你一钱银子",
            },
            {
                "type": "npc_encounter",
                "npc_id": "npc_buyer_outside",
                "weight": 2,
                "description": "牙行门口有外地客商在问路",
                "hint": "听口音像是从北边来的",
            },
            {
                "type": "market_event",
                "outcome_id": "silk_price_up",
                "weight": 1,
                "description": "今天的行情比昨天好——市面缺货",
                "hint": "这是好消息",
            },
        ],
    },
    # === 镇外桑田场景 ===
    {
        "id": "re_sangtian_weather",
        "trigger_condition": {
            "scene": "镇外桑田",
        },
        "probability": 0.3,
        "outcomes": [
            {
                "type": "weather",
                "outcome_id": "sudden_rain",
                "weight": 1,
                "description": "突然下起大雨，你被淋得透湿",
                "hint": "桑田里躲雨不便",
                "effect": {"silver_pressure": "+0.5"},  # 淋雨可能受寒
            },
            {
                "type": "npc_encounter",
                "npc_id": "npc_sangye_farmer",
                "weight": 2,
                "description": "一位老桑农在打理桑树",
                "hint": "他可能知道今年桑叶的行情",
            },
            {
                "type": "discovery",
                "outcome_id": "wild_mulberry",
                "weight": 1,
                "description": "你发现一片野桑林，桑叶很嫩",
                "hint": "可以省一些桑叶钱",
                "effect": {"livelihood": "+0.5"},
            },
        ],
    },
    # === 任何场景的"突遇"事件 ===
    {
        "id": "re_sudden_money",
        "trigger_condition": {
            "min_round": 8,
        },
        "probability": 0.1,  # 10%触发（稀有事件）
        "outcomes": [
            {
                "type": "money_event",
                "outcome_id": "pick_up_silver",
                "weight": 1,
                "description": "你在路上捡到了3钱碎银",
                "hint": "像是有人不小心掉的",
                "effect": {"silver": "+0.3"},
            },
            {
                "type": "money_event",
                "outcome_id": "lose_pocket",
                "weight": 1,
                "description": "你发现口袋被划破了，丢了2钱银子",
                "hint": "有人趁你不备摸了你的口袋",
                "effect": {"silver": "-0.2"},
            },
        ],
    },
    # === 自家作坊场景（家庭互动）===
    {
        "id": "re_family_event",
        "trigger_condition": {
            "scene": "自家作坊",
        },
        "probability": 0.25,
        "outcomes": [
            {
                "type": "family_interaction",
                "outcome_id": "wife_unwell",
                "weight": 1,
                "description": "沈氏身体不舒服，还在坚持做活",
                "hint": "她的脸色有些苍白",
                "effect": {"livelihood": "-0.3"},  # 生产力下降
            },
            {
                "type": "family_interaction",
                "outcome_id": "son_progress",
                "weight": 2,
                "description": "阿宝在院子里练字，背诵了一段《千字文》",
                "hint": "他进步了",
                "effect": {"livelihood": "+0.2"},
            },
            {
                "type": "family_interaction",
                "outcome_id": "neighbor_visit",
                "weight": 2,
                "description": "邻居周嫂子来串门，带了些自家种的菜",
                "hint": "人情往来",
            },
        ],
    },
]


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    if "random_events" not in config["world"]:
        config["world"]["random_events"] = RANDOM_EVENTS

    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 已添加 {len(RANDOM_EVENTS)} 个随机事件表:")
    for e in RANDOM_EVENTS:
        print(f"  {e['id']}: scene={e['trigger_condition'].get('scene', 'any')}, p={e['probability']}, {len(e['outcomes'])} outcomes")


if __name__ == "__main__":
    main()