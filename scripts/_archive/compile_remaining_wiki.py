"""写入剩余Wiki：支线路径v2.0 + 离乡路线v1.0

设计原则（基于评估结论）：
- knowledge.entries: 严格精简到<200字符
- narrative_snippets: 保留原文片段（<200字符）
- 不新增identity（避免CLI问询爆炸）
- 不新增identity_switch_offers（后续Phase再做）

支线v2.0 新增 8条entries + 6条snippets
离乡v1.0 新增 6条entries + 5条snippets
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")


# === 支线路径v2.0：8条精简entries ===

BRANCH_ENTRIES = [
    # 通用支线
    {
        "id": "sc_imperial_exam_path",
        "layer": "scene",
        "title": "科举阶梯与时间",
        "content": "完整路径：童生→秀才→举人→进士→授官。录取率：童生→秀才约10%（苏州府3000童生争120名额），秀才→举人约3-5%（多数人终老秀才），举人→进士约10%。科举必由学校，至少3-5年不事生产。",
        "trigger_keywords": ["科举", "秀才", "举人", "进士", "童生", "乡试", "会试", "院试"],
        "trigger_scene": ["茶馆", "县衙"],
        "related_entries": ["sc_women_status"],
        "source_refs": "陈宝良《明代秀才的生活世界》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "pr_xiucai_privileges",
        "layer": "principle",
        "title": "秀才的特权与生路",
        "content": "秀才特权：见官不跪（不受笞捶）、免役、'四民之首'、可穿特定衣服、可开私塾。经济来源：廪膳微薄；教书处馆月2-3两（温秀才西门庆家月3两）；代写书信；包揽钱粮（灰色）；充当干证（灰色）。'一衿终老'是常态。",
        "trigger_keywords": ["秀才", "免役", "西席", "处馆", "包揽", "生员", "读书"],
        "trigger_scene": ["茶馆", "县衙"],
        "related_entries": ["sc_imperial_exam_path"],
        "source_refs": "陈宝良《明代秀才的生活世界》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_jiangnan_underworld",
        "layer": "scene",
        "title": "江南市井灰色生态",
        "content": "五种灰色势力：牙人/牙郎（中间商，抽成3-5%）、讼师（代写诉状）、帮闲（依附权贵跑腿）、打行（职业打手）、胥吏（衙门跑腿操控基层）。与丝织户关系：卖绸必经牙人；纠纷需要讼师；可能被帮闲骚扰；胥吏卡赋税和诉讼。",
        "trigger_keywords": ["牙人", "讼师", "帮闲", "打行", "胥吏", "牙行", "中间商", "市井"],
        "trigger_scene": ["牙行", "县衙", "茶馆"],
        "related_entries": ["pr_silver_inflow"],
        "source_refs": "《金瓶梅》市井研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_dahang",
        "layer": "scene",
        "title": "打行：万历江南黑社会",
        "content": "起源嘉靖、万历年间苏州一带，后蔓延松江及整个江南。成员'皆系无家恶少'，后期富豪和衙役胥吏也加入，歃血为盟。独特打人方法：打胸、肋、下腹、腰背，可做到'定期死亡'——三个月或五个月后死，超出期限不用抵命。嘉靖三十八年朝廷曾调兵打击，但屡禁不止。",
        "trigger_keywords": ["打行", "恶少", "打人", "嘉靖", "万历", "苏州", "黑社会"],
        "trigger_scene": ["茶馆", "牙行"],
        "related_entries": ["sc_jiangnan_underworld"],
        "source_refs": "明代江南'打行'研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_ximen_qing_path",
        "layer": "scene",
        "title": "西门庆的发迹路径",
        "content": "西门庆路径：继承生药铺（起点）→娶富妾获嫁妆数千两→开缎子铺、放高利贷、包揽诉讼→行贿蔡太师获授提刑千户→家当约10万两。商业版图：生药铺/缎子铺/放贷/包揽/盐引。关键手段：娶妻敛财/行贿买官/结交权贵/信息垄断。",
        "trigger_keywords": ["西门庆", "缎子铺", "高利贷", "包揽", "盐引", "生药铺", "蔡太师"],
        "trigger_scene": ["茶馆", "牙行"],
        "related_entries": ["sc_jiangnan_underworld"],
        "source_refs": "《金瓶梅》第74回",
        "confidence": "high",
        "needs_review": False,
    },
    # 女性特有（v2.0新增）
    {
        "id": "sc_fujian_wind",
        "layer": "scene",
        "title": "妇健之风：江南女性真实处境",
        "content": "明代中后期江南出现'妇健'风气：劳动妇女很少缠足；'妻络夫织'是常态；妇女走出家庭参与经济；'友贾''卖婆''牙婆'是真实职业。江南丝织业中女性是核心劳动力。卜正民：随商业经济发展，女性从家庭附庸中获得部分解放。",
        "trigger_keywords": ["妇健", "友贾", "卖婆", "牙婆", "女贾", "明代女性", "缠足", "妻络夫织"],
        "trigger_scene": ["自家作坊", "盛泽市集"],
        "related_entries": ["sc_women_status", "sc_silk_workshop"],
        "source_refs": "卜正民《纵乐的困惑》；陈宝良《明代妇女》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_talented_women",
        "layer": "scene",
        "title": "才女/闺塾师路线",
        "content": "女性不可考科举（硬约束），但可走才女/闺塾师路线：高彦颐《闺塾师》指出明末江南女性有机会读书识字。阶段：识字→读书→写诗（加入女性诗社）→闺塾师（教富户女儿，月1-2两）→编书出版。优势：无科举独木桥、不需脱产、闺塾师稀缺。风险：'女子无才便是德'舆论、嫁人后可能被迫放弃。",
        "trigger_keywords": ["才女", "闺塾师", "叶家", "女性诗社", "女塾师", "才女文化"],
        "trigger_scene": ["自家作坊", "闺阁"],
        "related_entries": ["sc_fujian_wind", "sc_women_status"],
        "source_refs": "高彦颐《闺塾师》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_three_goddesses",
        "layer": "scene",
        "title": "三姑六婆：女性灰色势力",
        "content": "'三姑六婆'贬义但实际是明代市井**信息网络最发达群体**：牙婆进出各家各户，掌握人事/婚姻信息；媒婆了解未婚男女；卖婆在女性客户间穿针引线，比男牙人更容易进入闺阁；师婆/巫婆是女性求助的第一站。女性版'西门庆'路径：织户→卖婆→牙婆→女贾→控制丝织品流通→与官府内眷搭关系。",
        "trigger_keywords": ["三姑六婆", "牙婆", "媒婆", "卖婆", "师婆", "巫婆", "女贾", "王婆", "薛嫂"],
        "trigger_scene": ["自家作坊", "闺阁", "盛泽市集"],
        "related_entries": ["sc_fujian_wind", "sc_jiangnan_underworld"],
        "source_refs": "《金瓶梅》王婆/薛嫂/刘婆；《明代妇女》",
        "confidence": "high",
        "needs_review": False,
    },
]


# === 支线路径v2.0：6条snippets ===

BRANCH_SNIPPETS = [
    {
        "id": "sn_fanjin_zhongju",
        "source": "《儒林外史》范进中举",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["科举", "中举", "秀才", "考试"],
        "npc_use_case": "DM描述科举不易时引用——'你看范进，考了二十多次才中举'",
        "snippet_text": "秀才范进考了二十余次，54岁才中举。中举后喜极而疯，老丈人胡屠户一巴掌打醒。中举后'众人来奉承他：有送田产的，有送店房的'——一夜间从穷酸变富贵。",
        "target_gender": "all",
    },
    {
        "id": "sn_xu_wei_life",
        "source": "历史人物徐渭",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["秀才", "屡试不第", "杀妻", "生员"],
        "npc_use_case": "老秀才叹气时——'我当年跟徐渭一样，考到杀妻下狱'",
        "snippet_text": "绍兴秀才徐渭，八试不第。以卖文、入幕为生。后因杀妻下狱，被革去生员身份。一生在'读书人'和'谋生者'之间挣扎。",
        "target_gender": "all",
    },
    {
        "id": "sn_wen_xiucai",
        "source": "《金瓶梅》温秀才",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["西席", "教书", "包揽", "偷窥"],
        "npc_use_case": "NPC讲秀才两面——'你看西门庆家的温先生，读书人不一定是好人'",
        "snippet_text": "西门庆的代笔先生温秀才，月3两银子。表面儒雅，实则偷窥东家隐私、泄露书信、有断袖之癖。最终被赶走。'读书人'不等于'好人'。",
        "target_gender": "all",
    },
    {
        "id": "sn_wang_po",
        "source": "《金瓶梅》王婆",
        "applies_to_scenes": ["茶馆", "闺阁"],
        "trigger_keywords": ["茶馆", "牙婆", "撮合", "三姑六婆"],
        "npc_use_case": "NPC讲古——'你看王婆，靠撮合人和买卖丫鬟就发了家'",
        "snippet_text": "王婆是茶馆老板娘，实为牙婆/媒婆。撮合西门庆与潘金莲，是整个故事的关键推手。'十面埋伏'计策（潘驴邓小闲）展示了牙婆对人心的精准把握。",
        "target_gender": "female",
    },
    {
        "id": "sn_xue_sao",
        "source": "《金瓶梅》薛嫂",
        "applies_to_scenes": ["闺阁", "盛泽市集"],
        "trigger_keywords": ["媒婆", "说合", "信息掮客"],
        "npc_use_case": "DM描述媒婆嘴脸——'她对各家情况了如指掌'",
        "snippet_text": "薛嫂是专业媒婆，给西门庆说合了孟玉楼。能说会道，对各家情况了如指掌——'信息掮客'的女性版。",
        "target_gender": "female",
    },
    {
        "id": "sn_ye_family",
        "source": "历史人物叶绍袁家族",
        "applies_to_scenes": ["闺阁", "茶馆"],
        "trigger_keywords": ["才女", "吴江", "叶家", "诗社"],
        "npc_use_case": "NPC羡慕——'吴江叶家，一门才女'",
        "snippet_text": "吴江叶氏一门才女。叶绍袁之妻沈宜修、女叶小鸾、叶纨纨皆能诗。叶小鸾十七岁早逝，留下诗稿，成为江南才女传奇。盛泽镇距吴江不远，玩家可能听说过叶家。",
        "target_gender": "female",
    },
]


# === 离乡路线v1.0：6条精简entries ===

TRAVEL_ENTRIES = [
    {
        "id": "bg_population_mobility",
        "layer": "background",
        "title": "万历年间人口流动",
        "content": "明中叶后朝廷放弃迫使流民返回原籍。一条鞭法后赋役折银，人身控制松弛。江南人外出经商/游学/谋生已是常态。关津制（路引）执行松懈。离乡硬约束：路引（松弛执行）/户籍（仍要交税）/路费/人脉。",
        "trigger_keywords": ["离乡", "路引", "户籍", "流动", "关津", "出远门"],
        "trigger_scene": [],
        "related_entries": ["pr_silver_inflow"],
        "source_refs": "明代人口流动研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "bg_longqing_kaihai",
        "layer": "background",
        "title": "隆庆开关与月港",
        "content": "1567年明廷解除海禁，月港（福建漳州海澄）成为唯一合法民间海外贸易港。到万历十五年（1587）月港已繁荣20年，被称为'天子之南库'，通商47国，18条航线，1公里江岸7座渡口。开关规定不得到日本贸易。",
        "trigger_keywords": ["隆庆开关", "月港", "海澄", "海禁", "海商", "丝客"],
        "trigger_scene": [],
        "related_entries": ["bg_population_mobility", "pr_silver_inflow"],
        "source_refs": "袁灿兴《朝贡贸易与战争》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_yue_gang_life",
        "layer": "scene",
        "title": "月港海商生活",
        "content": "盛泽→月港：8-12天，6-10两（船资3-5/食宿2-3/税1-2）。月港商机：盛泽丝绸是硬通货；可做'丝客'收丝到月港卖；也可搭船出海。风险：闽南商人抱团、官府税重（督饷馆）、海上风浪海盗。",
        "trigger_keywords": ["月港", "海澄", "丝客", "海商", "海上", "渡口"],
        "trigger_scene": ["牙行", "盛泽市集"],
        "related_entries": ["bg_longqing_kaihai"],
        "source_refs": "漳州月港研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_nanyang_sea_route",
        "layer": "scene",
        "title": "下南洋航线",
        "content": "盛泽→马尼拉：30-50天/单程，25-45两（不含货本）。吕宋（马尼拉）有西班牙大帆船贸易，一匹丝绸在马尼拉售价是进价3-5倍。风险：海上风浪高/海盗中/西班牙重税高/疾病高/回不来中。月港季风：5-7月南风去，10-12月北风回。",
        "trigger_keywords": ["南洋", "马尼拉", "吕宋", "大帆船", "西班牙", "下海"],
        "trigger_scene": ["牙行", "茶馆"],
        "related_entries": ["bg_longqing_kaihai", "pr_silver_inflow"],
        "source_refs": "贡德·弗兰克《白银资本》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_grand_canal",
        "layer": "scene",
        "title": "京杭大运河",
        "content": "盛泽→北京：20-25天/顺利，12-20两。最常规远行路线。分段：盛泽→苏州→镇江→扬州→淮安→徐州→济宁→临清→天津→北京。黄河段最险（徐州段），济宁闸门多要等。京城：万历十五年北京人口百万，丝绸好货但江南商人已有行会，可投奔苏州会馆。",
        "trigger_keywords": ["运河", "京城", "北京", "南下", "北上", "会通河", "黄河段"],
        "trigger_scene": ["茶馆", "牙行"],
        "related_entries": ["sc_waterways"],
        "source_refs": "京杭大运河研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_ming_army_recruit",
        "layer": "scene",
        "title": "万历募兵制",
        "content": "卫所制名存实亡，募兵成为主流。月粮：九边1-1.5两/京营1两/地方营兵0.8-1两/水师1两。万历十五年无大战，但九边常年需兵。1587年辽东局势紧张（努尔哈赤1583起兵），5年后1592朝鲜之役。风险：军官克扣（极高）、被当苦力、将领私人化（募兵只认将不认国）。女性不能正式参军（硬约束）。",
        "trigger_keywords": ["募兵", "九边", "参军", "卫所", "辽东", "月粮", "投军"],
        "trigger_scene": ["茶馆", "县衙"],
        "related_entries": [],
        "source_refs": "明代募兵制研究",
        "confidence": "high",
        "needs_review": False,
    },
]


# === 离乡路线v1.0：5条snippets ===

TRAVEL_SNIPPETS = [
    {
        "id": "sn_yuegang_silk",
        "source": "万历海商口述",
        "applies_to_scenes": ["牙行", "盛泽市集"],
        "trigger_keywords": ["月港", "海澄", "丝绸换白银", "丝客"],
        "npc_use_case": "NPC聊出海——'月港那边一匹湖绫能卖三两'",
        "snippet_text": "月港那边，一匹湖绫能卖到三两银子，是这边的好几倍……盛泽的丝绸在月港是硬通货。",
        "target_gender": "all",
    },
    {
        "id": "sn_lvson_silver",
        "source": "万历海商口述",
        "applies_to_scenes": ["茶馆", "牙行"],
        "trigger_keywords": ["南洋", "马尼拉", "吕宋", "白银", "大帆船"],
        "npc_use_case": "NPC讲南洋暴利——'一匹下去，三倍回来'",
        "snippet_text": "你要是带十匹湖绫下去，到马尼拉至少翻三倍。西班牙人在那头大帆船等着呢，把丝绸运到美洲换白银。",
        "target_gender": "all",
    },
    {
        "id": "sn_japan_prohibited",
        "source": "明代私商口述",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["东洋", "日本", "平户", "走私", "违禁"],
        "npc_use_case": "神秘商人低声——'你要是敢走一趟东洋……'",
        "snippet_text": "你要是敢走一趟东洋，十匹绸子换回来的银子够你买一栋楼……但上个月刚抓了三个，杀头的买卖。",
        "target_gender": "male",  # 女性几乎不可能
    },
    {
        "id": "sn_canal_danger",
        "source": "运河船夫口述",
        "applies_to_scenes": ["茶馆", "牙行"],
        "trigger_keywords": ["运河", "黄河", "翻船", "北上"],
        "npc_use_case": "老人回忆——'我年轻时走过一趟运河，黄河段差点翻船'",
        "snippet_text": "我年轻时走过一趟运河，黄河段差点翻船。徐州那一段水急浪大，闸门又多，等了三天。再也不敢走了。",
        "target_gender": "all",
    },
    {
        "id": "sn_army_koukou",
        "source": "明代老兵口述",
        "applies_to_scenes": ["茶馆", "县衙"],
        "trigger_keywords": ["投军", "募兵", "月粮", "克扣", "九边"],
        "npc_use_case": "老兵警告——'别信那月粮，到手能有八钱就不错了'",
        "snippet_text": "别信那月粮一两五钱，到手能有八钱就不错了。军官吃空饷是天经地义的。但好歹有口饭吃，比饿死强。",
        "target_gender": "male",
    },
]


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    # 1. 追加entries
    existing_entry_ids = {e["id"] for e in config["knowledge"]["entries"]}
    added_entries = 0
    for entry in BRANCH_ENTRIES + TRAVEL_ENTRIES:
        if entry["id"] not in existing_entry_ids:
            config["knowledge"]["entries"].append(entry)
            added_entries += 1

    # 2. 追加snippets
    existing_snip_ids = {s["id"] for s in config["knowledge"]["narrative_snippets"]}
    added_snippets = 0
    for snip in BRANCH_SNIPPETS + TRAVEL_SNIPPETS:
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

    print(f"✅ 添加entries: {added_entries}条（支线{len(BRANCH_ENTRIES)}+离乡{len(TRAVEL_ENTRIES)}）")
    print(f"✅ 添加snippets: {added_snippets}条（支线{len(BRANCH_SNIPPETS)}+离乡{len(TRAVEL_SNIPPETS)}）")
    print(f"📊 当前 totals: entries={total_entries}, snippets={total_snippets}")
    print(f"📊 era.json大小: {era_size} 字符 (~{era_size // 1024}KB)")


if __name__ == "__main__":
    main()