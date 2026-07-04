"""在era.json里添加story_segments字段

设计：
- 按scene分类（盛泽市集/茶馆/牙行/自家作坊/镇外桑田/县衙/闺阁）
- 每条segment有type字段（atmosphere/npc_dialog/transaction/rumor/description）
- LLM按scene+type随机抽取片段，自由组合故事
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")

# === story_segments：按scene分类的叙事片段 ===

STORY_SEGMENTS = {
    "盛泽市集": [
        {
            "id": "seg_market_atmos_01",
            "type": "atmosphere",
            "text": "盛泽镇丝绸业繁盛，镇上绸丝牙行，约有千百余家，远近村坊织成绸匹，俱到此上市。四方商贾来收买的，蜂攒蚁集，挨挤不开。",
            "keywords": ["市集", "丝市", "牙行", "盛泽"],
        },
        {
            "id": "seg_market_atmos_02",
            "type": "atmosphere",
            "text": "镇上居民稠广，土俗淳朴，俱以蚕桑为生。男女勤谨，络纬机杼之声，通宵彻夜。那岸上两岸绸丝牙行，约有千百余家。",
            "keywords": ["市集", "桑蚕", "织机"],
        },
        {
            "id": "seg_market_atmos_03",
            "type": "atmosphere",
            "text": "市集上人来人往，小贩的叫卖声、驴马的嘶鸣、秤砣的叮当声交织在一起。空气里弥漫着染料和酒糟的味道。",
            "keywords": ["市集", "小贩", "叫卖"],
        },
        {
            "id": "seg_market_npc_01",
            "type": "npc_dialog",
            "npc_role": "牙人",
            "text": "客官，今年的丝价比去年涨了一成，您这批货成色不错，我给您个公道价——三两五钱银子，怎么样？",
            "keywords": ["牙人", "丝价", "议价"],
        },
        {
            "id": "seg_market_npc_02",
            "type": "npc_dialog",
            "npc_role": "老织户",
            "text": "哎，今年丝是不错，可这税也重啊。我那小儿子天天念叨着去月港——你说，他一个织户，去了能干啥？",
            "keywords": ["老织户", "税", "月港"],
        },
        {
            "id": "seg_market_npc_03",
            "type": "npc_dialog",
            "npc_role": "卖货郎",
            "text": "苏州来的胭脂水粉，要不要看看？还有上好的针线——给娘子买一盒吧！",
            "keywords": ["卖货郎", "胭脂", "针线"],
        },
        {
            "id": "seg_market_transaction_01",
            "type": "transaction",
            "text": "你从怀里掏出上个月织的三匹湖绫，交给牙行验成色。牙人拿着对着光翻来覆去看了半天，最后捻了捻丝线。",
            "keywords": ["卖绸", "验成色", "湖绫"],
        },
        {
            "id": "seg_market_rumor_01",
            "type": "rumor",
            "text": "你听人说，今年第一批洋船要来了，洋船一来，丝价怕是要涨——但谁知道呢，去年的洋船也说过这话。",
            "keywords": ["洋船", "丝价", "传言"],
        },
    ],
    "茶馆": [
        {
            "id": "seg_teahouse_atmos_01",
            "type": "atmosphere",
            "text": "茶馆里人声鼎沸，几张八仙桌坐满了人。有人在高谈阔论，有人在低声密谈，茶博士端着铜壶来回穿梭。",
            "keywords": ["茶馆", "茶博士", "人声"],
        },
        {
            "id": "seg_teahouse_atmos_02",
            "type": "atmosphere",
            "text": "吴老板的茶馆是盛泽镇上消息最灵通的地方。三教九流都在这里出现——商人、秀才、牙人、甚至偶尔有外地来的僧道。",
            "keywords": ["茶馆", "吴老板", "三教九流"],
        },
        {
            "id": "seg_teahouse_rumor_01",
            "type": "rumor",
            "text": "有人说，松江那边的华亭县，董其昌家的仆人砸了生员陆兆芳的门，强行搜走了一个婢女。这事闹得满城风雨。",
            "keywords": ["董其昌", "陆兆芳", "生员"],
        },
        {
            "id": "seg_teahouse_rumor_02",
            "type": "rumor",
            "text": "癞痢头阿福晃了进来，被几个人拉住问这问那，嘻嘻哈哈地应付着——他什么都知道一点，但什么都不肯说全。",
            "keywords": ["阿福", "消息灵通"],
        },
        {
            "id": "seg_teahouse_rumor_03",
            "type": "rumor",
            "text": "你听见隔壁桌在议论：'我听说月港那边，一匹湖绫能卖到三两银子，是这边的好几倍……'",
            "keywords": ["月港", "湖绫", "丝价"],
        },
        {
            "id": "seg_teahouse_npc_01",
            "type": "npc_dialog",
            "npc_role": "老秀才",
            "text": "我当年也是织户出身，读了二十年书，如今……唉。一衿终老，那是常态。",
            "keywords": ["秀才", "科举", "读书"],
        },
        {
            "id": "seg_teahouse_npc_02",
            "type": "npc_dialog",
            "npc_role": "客商",
            "text": "客官，从哪里来的？我做的是苏杭丝绸生意，往来京城、临清都有门路。",
            "keywords": ["客商", "丝绸", "京城"],
        },
    ],
    "牙行": [
        {
            "id": "seg_yahang_atmos_01",
            "type": "atmosphere",
            "text": "牙行里光线昏暗，空气中弥漫着染料和霉味。墙上挂着一张张丝绸样品，五颜六色，从素白到朱红。",
            "keywords": ["牙行", "丝绸样品"],
        },
        {
            "id": "seg_yahang_npc_01",
            "type": "npc_dialog",
            "npc_role": "牙行老板",
            "text": "你的这批货成色不算顶好——市面上这种货色多的是。不过老主顾了，三两二钱，不能再多了。",
            "keywords": ["牙行老板", "压价", "成色"],
        },
        {
            "id": "seg_yahang_npc_02",
            "type": "npc_dialog",
            "npc_role": "牙行学徒",
            "text": "老板，外面有个外地面孔的客商，说是要找五百匹细绢……",
            "keywords": ["学徒", "客商", "细绢"],
        },
        {
            "id": "seg_yahang_rumor_01",
            "type": "rumor",
            "text": "你隐约听见牙人在背后嘀咕：'这批货转手到月港至少翻一倍……可惜咱们没那路子'",
            "keywords": ["牙人", "月港", "转手"],
        },
    ],
    "自家作坊": [
        {
            "id": "seg_home_atmos_01",
            "type": "atmosphere",
            "text": "灶房里传来沈氏生火的声音。阿宝从后院跑出来，喊着'爹，娘说粥好了'。织机静静地靠在墙边，经线还剩一半没理。",
            "keywords": ["自家", "沈氏", "阿宝", "织机"],
        },
        {
            "id": "seg_home_atmos_02",
            "type": "atmosphere",
            "text": "早晨的盛泽镇还笼着一层薄雾。巷子里传来挑水的吱呀声，还有远处牙行方向隐约的吆喝。",
            "keywords": ["盛泽", "早晨", "薄雾"],
        },
        {
            "id": "seg_home_npc_01",
            "type": "npc_dialog",
            "npc_role": "沈氏（妻）",
            "text": "相公，邻家周嫂子说镇上有人家嫁女儿，要赶做几匹绸缎压箱底，问咱家有没有好湖绫……",
            "keywords": ["沈氏", "嫁妆", "湖绫"],
        },
        {
            "id": "seg_home_npc_02",
            "type": "npc_dialog",
            "npc_role": "阿宝（子）",
            "text": "爹！今天先生教我写了个'人'字！你看！",
            "keywords": ["阿宝", "私塾", "写字"],
        },
    ],
    "镇外桑田": [
        {
            "id": "seg_sangtian_atmos_01",
            "type": "atmosphere",
            "text": "出镇不到二里，就是一片片桑田。时值春末，桑叶长得正好，绿油油的，远处有几户农家在采叶。",
            "keywords": ["桑田", "春末", "采叶"],
        },
        {
            "id": "seg_sangtian_atmos_02",
            "type": "atmosphere",
            "text": "桑树林里静悄悄的，只有风吹过桑叶的沙沙声。阳光透过叶缝洒下来，斑斑点点。",
            "keywords": ["桑田", "桑叶"],
        },
        {
            "id": "seg_sangtian_npc_01",
            "type": "npc_dialog",
            "npc_role": "老桑农",
            "text": "客官也是来收桑叶的？今年雨水足，叶子好，但价钱也涨了些——要不您看看我这片？",
            "keywords": ["桑农", "桑叶", "价钱"],
        },
        {
            "id": "seg_sangtian_rumor_01",
            "type": "rumor",
            "text": "听说隔壁村里有人家养蚕失败，一家人今年只能喝西北风——蚕这玩意儿，比养孩子还娇贵。",
            "keywords": ["养蚕", "失败"],
        },
    ],
    "县衙": [
        {
            "id": "seg_yamen_atmos_01",
            "type": "atmosphere",
            "text": "县衙门前立着两块石碑——'戒石亭'、'诬告加三等'。几个衙役懒洋洋地靠在门柱上，看见人来就伸手要'门包'。",
            "keywords": ["县衙", "戒石亭", "门包"],
        },
        {
            "id": "seg_yamen_npc_01",
            "type": "npc_dialog",
            "npc_role": "胥吏",
            "text": "您这事啊，得从长计议——我们这儿衙门口的规矩您也懂，'规礼'是少不了的。",
            "keywords": ["胥吏", "规礼", "办事"],
        },
        {
            "id": "seg_yamen_rumor_01",
            "type": "rumor",
            "text": "你听见旁边的老乡在低声议论：'今年的税单比去年又重了两成——这日子没法过了'",
            "keywords": ["税", "税单", "议论"],
        },
    ],
    "闺阁": [
        {
            "id": "seg_guige_atmos_01",
            "type": "atmosphere",
            "text": "内宅里挂着一幅绣着牡丹的中堂，绣工精细，颜色还是鲜亮的。女眷们围坐在八仙桌旁，手里做着针线。",
            "keywords": ["内宅", "绣品", "女眷"],
        },
        {
            "id": "seg_guige_npc_01",
            "type": "npc_dialog",
            "npc_role": "卖婆",
            "text": "太太，这是从杭州新进的湖绸，您摸摸这手感——比去年那批还细密。给小姐做嫁衣正合适。",
            "keywords": ["卖婆", "湖绸", "嫁衣"],
        },
    ],
}


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    if "knowledge" not in config:
        config["knowledge"] = {}
    if "story_segments" not in config["knowledge"]:
        config["knowledge"]["story_segments"] = STORY_SEGMENTS

    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = sum(len(segs) for segs in STORY_SEGMENTS.values())
    print(f"✅ 已添加 story_segments: {len(STORY_SEGMENTS)}个场景, {total}条片段")
    for scene, segs in STORY_SEGMENTS.items():
        print(f"  {scene}: {len(segs)}条")


if __name__ == "__main__":
    main()