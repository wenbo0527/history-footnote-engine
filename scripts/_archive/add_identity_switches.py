"""在era.json里添加identity_switch_offers配置

配置原则：
- 每条offer: from_identity -> to_identity
- trigger_condition: 满足条件后LLM会考虑发起offer
- llm_decides=true: 满足条件后LLM自行决定是否发起（不是100%触发）
- prompt_hint: 告诉LLM在什么场景下考虑发起
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

IDENTITY_SWITCH_OFFERS = [
    # === 女性身份切换 ===
    {
        "id": "weaving_f_to_scholar_f",
        "from_identity": "weaving_female",
        "to_identity": "scholar_female",
        "trigger_condition": {
            "min_round": 15,
            "min_silver_pressure_lt": 7,  # 银荒不太严重时
            "required_insights_any": ["ins_silk_trade", "ins_silver_tax", "ins_city_life"],
        },
        "prompt_hint": "DM在以下情况可以提供此选项：\n- 富户内眷请你教女儿识字/写诗\n- 诗社朋友邀你参加\n- 有人夸你'不识可惜'\n- 你在茶馆听到有才女的事迹\n\n但要注意：此路径对女性风险大（'女子无才便是德'舆论、嫁人后可能被迫放弃），DM应自然引入风险提示。",
        "llm_decides": True,
        "cost_description": "需要1-2年不事生产，全靠丈夫或积蓄支持；可能面临'女子无才便是德'的舆论压力",
        "benefit_description": "成为闺塾师，建立女性文人圈子；诗名远播后可编书出版",
    },
    {
        "id": "weaving_f_to_merchant_f",
        "from_identity": "weaving_female",
        "to_identity": "merchant_female",
        "trigger_condition": {
            "min_round": 10,
            "min_silver_pressure_lt": 8,
            "required_insights_any": ["ins_silk_trade"],
        },
        "prompt_hint": "DM在以下情况可以提供此选项：\n- 卖婆上门收购丝绸，看中你的成色经验，邀请你入行\n- 牙婆看中你的丝织经验，邀请你做'掮客'\n- 闺蜜劝你'别只守着织机'\n- 富户内眷请你去帮忙\n- 亡夫后无以为继（特殊场景）\n\n注意：卖婆/牙婆/媒婆是'三姑六婆'，社会评价低但信息网络发达，DM应客观呈现两面性。",
        "llm_decides": True,
        "cost_description": "放弃现有织机和人脉，需重新建立客户关系；社会评价低，被污名化风险",
        "benefit_description": "可以进入富户内宅，建立三姑六婆信息网络；经济独立，不依赖丈夫",
    },
    # === 男性身份切换 ===
    {
        "id": "weaving_m_to_scholar_m",
        "from_identity": "weaving_male",
        "to_identity": "scholar_male",
        "trigger_condition": {
            "min_round": 10,
            "min_silver_pressure_lt": 8,
            "required_insights_any": ["ins_silk_trade", "ins_silver_tax"],
        },
        "prompt_hint": "DM在以下情况可以提供此选项：\n- 儿子阿宝在私塾表现好，先生夸'可造之材'，家里讨论要不要全力供他读书\n- 行会里有人劝你'让儿子读书吧'\n- 李秀才酒后叹息科举不易\n- 镇上有人考中秀才的喜讯\n\n但注意：科举成功率极低（举人几千分之一），DM应自然引入风险。",
        "llm_decides": True,
        "cost_description": "需要3-5年不事生产（家计要靠妻子）；读书失败风险高，可能'一衿终老'",
        "benefit_description": "见官不跪的特权；可设馆教书；中举后是阶层跃迁",
    },
    {
        "id": "weaving_m_to_merchant_m",
        "from_identity": "weaving_male",
        "to_identity": "merchant_male",
        "trigger_condition": {
            "min_round": 10,
            "min_silver_pressure_lt": 7,
            "min_livelihood_gte": 4,  # 生计稳定
            "required_insights_any": ["ins_silk_trade"],
        },
        "prompt_hint": "DM在以下情况可以提供此选项：\n- 王掌柜暗示'你要是做中间商，比织布强'\n- 你帮客商验成色，客商说'你眼力好，自己干这行算了'\n- 老织户说'我当年也是织户，后来改做牙人'\n- 你手里有了本钱，思考下一步\n\n注意：商人社会地位低（'士农工商'末流），但收入高。",
        "llm_decides": True,
        "cost_description": "社会地位下降（'商人'在万历朝是末等）；需要启动资金；同行排挤",
        "benefit_description": "收入提高3-5倍；不用日日操劳织机；可雇佣别人做",
    },
    # === 后续支线（Phase 2/3）===
    # 1. weaving -> 弃织从商
    # 2. weaving -> 弃织从文
    # 3. scholar -> 弃文从商（屡试不第后）
    # 4. merchant -> 官商一体（行贿买官身）
    # 等
]


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    if "identity_switch_offers" not in config["world"]:
        config["world"]["identity_switch_offers"] = IDENTITY_SWITCH_OFFERS

    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 已添加 {len(IDENTITY_SWITCH_OFFERS)} 个身份切换选项:")
    for offer in IDENTITY_SWITCH_OFFERS:
        print(f"  {offer['id']}: {offer['from_identity']} → {offer['to_identity']}")


if __name__ == "__main__":
    main()
