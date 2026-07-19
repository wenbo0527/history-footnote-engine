"""把单player_identity扩展为多player_identities

v1.0只有一种"丝织户（默认男性）"。
v1.1扩展：
- weaving_male：丝织户·男（保留原配置）
- weaving_female：丝织户·女（调整边界+叙事）

后续Phase可继续扩展：
- scholar_male/female（读书人/才女）
- merchant_male/female（牙人/卖婆）
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")


# 现有identity作为男性版基础
BASE_IDENTITY = {
    "role": "江南丝织户",
    "social_class": "匠户",
    "location": "苏州府吴江县盛泽镇",
    "description": "你是一家小丝织作坊的主人，有两台织机，靠织造丝绸为生。盛泽镇是江南新兴的丝绸市镇，商贾云集，但你只是个手艺人，不是大商人。",
    "action_boundaries": {
        "can_access": ["自家作坊", "盛泽市集", "牙行", "茶馆", "镇上商铺", "邻居家", "镇外桑田", "县衙（递状子）"],
        "cannot_access": ["府衙以上官署", "皇宫", "军营", "边关", "科举考场"],
        "can_interact_with": ["家人", "雇工", "同行织户", "牙行经纪人", "商贩", "里长", "邻人", "镇上读书人", "过往客商"],
        "cannot_influence": ["皇帝决策", "朝廷人事", "军事部署", "税法制定", "科举结果"],
        "information_access": "市井传闻、牙行行情、里长传达的官府告示、茶馆闲谈、商客带来的远方消息",
    },
    "default_npc_relations": ["沈氏（妻）", "阿宝（子）", "小妹（女）", "张寡妇（邻）"],
}


PLAYER_IDENTITIES = {
    "weaving_male": {
        "id": "weaving_male",
        "label": "丝织户（男）",
        "gender": "male",
        "role": "江南丝织户·丈夫",
        "social_class": "匠户",
        "location": "苏州府吴江县盛泽镇",
        "description": "你是一家小丝织作坊的男主人，'妻络夫织'——你负责织造，妻子沈氏负责缫丝和家务。两台织机，是一家老小的命根子。",
        "action_boundaries": BASE_IDENTITY["action_boundaries"],
        "default_family_role": "丈夫",
        "starting_relationships": {
            "fm_wife": "妻子（沈氏）",
            "fm_son": "儿子（阿宝）",
            "fm_daughter": "女儿（小妹）",
        },
    },
    "weaving_female": {
        "id": "weaving_female",
        "label": "丝织户（女）",
        "gender": "female",
        "role": "江南丝织户·妻子",
        "social_class": "匠户",
        "location": "苏州府吴江县盛泽镇",
        "description": "你嫁到盛泽镇已经八年，夫家开着一间小丝织作坊。你是'妻络夫织'里的'络'——负责缫丝、染丝、协助织造，是丝织业真正的核心劳动力。丈夫负责外面的接单和粗活。",
        "action_boundaries": {
            "can_access": ["自家作坊", "盛泽市集（与丈夫同行）", "牙行（有丈夫或男性亲属在场）", "茶馆（与丈夫同行）", "镇上商铺", "邻居家（同上）", "镇外桑田（同上）", "庙宇", "闺阁（女性客户家）"],
            "cannot_access": [
                "科举考场",
                "府衙以上官署（不能独立出面）",
                "皇宫",
                "军营",
                "边关",
                "男性专属娱乐场所（高档酒楼、青楼）",
            ],
            "can_interact_with": [
                "家人",
                "同行织户女性",
                "牙婆/卖婆/媒婆",
                "闺塾师/女伴",
                "女性客户（富户内眷）",
                "邻里妇人",
                "过往客商女性眷属",
            ],
            "cannot_influence": [
                "皇帝决策",
                "朝廷人事",
                "军事部署",
                "税法制定",
                "科举结果",
                "独立签署商业契约（需男性亲属代签）",
            ],
            "information_access": "市井传闻、牙行行情、女伴间消息、茶馆女眷区闲谈、卖婆走门串户带来的消息、寺庙香客间流传",
            "special_access": {
                "闺阁": "可以进入富户内宅与女眷直接交谈——这是男性进不去的空间",
                "三姑六婆网络": "可以通过卖婆/牙婆/媒婆获取其他家庭内部信息",
            },
        },
        "default_family_role": "妻子",
        "starting_relationships": {
            "fm_husband": "丈夫",
            "fm_son": "儿子（阿宝）",
            "fm_daughter": "女儿（小妹）",
            "fm_mother_in_law": "婆婆（可选）",
        },
        "special_abilities": {
            "丝织技术": "缫丝、染丝、辨丝成色——比丈夫更懂行",
            "闺阁网络": "可以进入男性无法进入的女性社交空间",
            "三姑六婆": "卖婆/牙婆/媒婆是潜在的信息来源与合作对象",
        },
    },
    "scholar_male": {
        "id": "scholar_male",
        "label": "读书人（男）",
        "gender": "male",
        "role": "弃织从文的年轻织户",
        "social_class": "匠户（试图跻身士）",
        "location": "苏州府吴江县盛泽镇",
        "description": "你原本是丝织户子弟，但志不在织机。家里省吃俭用供你读书，你已经考中秀才，下一步是考举人。但科举之路荆棘满途——'一衿终老'是常态。",
        "action_boundaries": {
            "can_access": ["自家作坊", "盛泽市集", "牙行", "茶馆", "镇上商铺", "文社", "县学（秀才身份）", "县衙（见官不跪）"],
            "cannot_access": ["府衙以上官署（无官身）", "皇宫", "军营"],
            "can_interact_with": ["家人", "同学秀才", "座师（考官）", "富户（受聘为西席）", "乡绅", "同窗"],
            "cannot_influence": ["皇帝决策", "朝廷人事", "军事部署", "税法制定"],
            "information_access": "文社议论、座师提点、乡绅闲谈、科举时文选辑",
        },
        "default_family_role": "读书的儿子",
        "starting_relationships": {
            "fm_father": "父亲（织户）",
            "fm_mother": "母亲",
        },
    },
    "scholar_female": {
        "id": "scholar_female",
        "label": "才女/闺塾师（女）",
        "gender": "female",
        "role": "江南才女或闺塾师",
        "social_class": "匠户（试图跻身上层）",
        "location": "苏州府吴江县盛泽镇",
        "description": "你出身丝织户，但自幼聪慧，识文断字。明末江南才女文化繁盛——你或在家中教弟妹读书，或被请去大户人家当闺塾师。但'女子无才便是德'的舆论压力始终存在。",
        "action_boundaries": {
            "can_access": ["自家作坊", "盛泽市集", "牙行（与家人同行）", "富户内宅（闺塾师身份）", "女伴圈子", "诗社", "寺庙", "茶馆（女眷区）"],
            "cannot_access": ["科举考场", "文社（男性专属）", "府衙以上官署（不能独立出面）", "皇宫", "军营"],
            "can_interact_with": ["家人", "女伴（才女圈子）", "富户内眷（雇主）", "闺中弟子", "女塾师前辈", "通过内眷间接影响官府"],
            "cannot_influence": ["科举结果（硬约束）", "朝廷人事", "独立签署商业契约"],
            "information_access": "女伴间诗酒唱和、闺塾雇主家内宅消息、寺庙香客间流传、女红圈手工艺信息",
            "special_access": {
                "闺阁": "可以进入富户内宅与女眷长时间接触——这是男性进不去的",
                "诗社": "女性诗社是独特的社交网络",
            },
        },
        "default_family_role": "女儿/闺塾师",
        "starting_relationships": {
            "fm_father": "父亲（织户）",
            "fm_mother": "母亲",
            "fm_patroness": "雇主（富户内眷）",
        },
        "special_abilities": {
            "诗词文赋": "明末江南才女文化的核心能力",
            "闺塾教学": "教富户女儿读书——稀缺资源",
            "女性视角的诗文": "进入男性无法进入的闺阁",
        },
    },
    "merchant_male": {
        "id": "merchant_male",
        "label": "牙人/中间商（男）",
        "gender": "male",
        "role": "丝织品牙人",
        "social_class": "商人（不入流）",
        "location": "苏州府吴江县盛泽镇",
        "description": "你原来是丝织户或雇工，后来攒了点本钱做了牙人——撮合织户和客商，抽取3-5%佣金。商人在明代社会地位不高，但你已经摸到了市井的门道。",
        "action_boundaries": {
            "can_access": ["自家牙行", "盛泽市集", "织户家", "茶馆", "酒楼", "县衙（需打点）", "行会"],
            "cannot_access": ["科举考场", "皇宫", "军营"],
            "can_interact_with": ["织户", "客商", "牙行同行", "行会首事", "胥吏（需打点）", "帮闲"],
            "cannot_influence": ["科举结果", "朝廷决策"],
            "information_access": "客商带来的远方消息、牙行内部情报、行会消息、茶馆闲谈",
        },
        "default_family_role": "牙人",
        "starting_relationships": {
            "npc_wang": "王掌柜（行会头目）",
        },
    },
    "merchant_female": {
        "id": "merchant_female",
        "label": "卖婆/牙婆（女）",
        "gender": "female",
        "role": "女性中间商",
        "social_class": "三姑六婆（社会评价低）",
        "location": "苏州府吴江县盛泽镇",
        "description": "你是'三姑六婆'中的牙婆或卖婆——在闺阁间穿针引线，撮合买卖、说合婚事、传递消息。社会评价低但信息网络发达。",
        "action_boundaries": {
            "can_access": ["自家", "盛泽市集", "富户内宅（核心优势）", "牙行（与丈夫/搭档）", "寺庙", "女伴圈子", "媒婆行会"],
            "cannot_access": ["科举考场", "男性专属娱乐场所", "府衙（不能独立出面）"],
            "can_interact_with": ["女性客户（核心）", "富户内眷", "媒婆同行", "牙婆同行", "师婆/巫婆", "通过内眷间接影响官府"],
            "cannot_influence": ["科举结果（硬约束）", "朝廷决策", "独立签署大额契约"],
            "information_access": "闺阁内宅消息（核心）、女伴间消息、寺庙香客、媒婆信息网络、牙行行情",
            "special_access": {
                "闺阁": "可以频繁进入富户内宅——男性的禁区",
                "三姑六婆网络": "牙婆/媒婆/卖婆/师婆——信息掮客群",
            },
        },
        "default_family_role": "牙婆",
        "starting_relationships": {
            "npc_li": "李秀才有断袖之癖（男性sao类人）",
            "npc_zhang": "张寡妇（同行）",
        },
        "special_abilities": {
            "闺阁网络": "可进入富户内宅——明代最封闭的空间",
            "三姑六婆信息": "掌握各家未婚女性、丫鬟、婚姻信息",
            "成事说合": "撮合买卖、婚事——佣金收入",
        },
    },
}


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    # 1. 移除旧的player_identity
    if "player_identity" in config["world"]:
        del config["world"]["player_identity"]

    # 2. 添加player_identities
    config["world"]["player_identities"] = PLAYER_IDENTITIES

    # 3. 添加默认选择
    config["world"]["default_identity"] = "weaving_male"

    # 4. 写回
    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 已添加 {len(PLAYER_IDENTITIES)} 个身份:")
    for key, identity in PLAYER_IDENTITIES.items():
        print(f"  - {key} ({identity['gender']}): {identity['label']}")


if __name__ == "__main__":
    main()
