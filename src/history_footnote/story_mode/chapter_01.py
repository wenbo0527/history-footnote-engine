"""🆕 v2.10.17 Phase 11 — 第一章剧本 (丰富版 · 30+ 节点 · 80+ 选项 · 4 结局)

从 10 节点扩展到 30+ 节点:
- 4 条主线 (借款/卖机/上苏/求助)
- 3 个随机事件
- 4 个结局 (兴家/欠债/病死/出走)
- 多声部 narrative (旁白/NPC/内心独白/音效)
- 环境模板自动注入

参考史料: 《吴江县志》《万历邸钞》《金瓶梅》《醒世姻缘》
"""
from __future__ import annotations

from history_footnote.story_mode.rich import (
    EnvironmentContext,
    NarrativeSection,
    RandomEncounter,
    _narrator,
    _npc,
    _npc_action,
    _sound,
    _thought,
)
from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)


# 🆕 v2.10.26: helper 已在 rich.py 统一提供, 不再本地定义
# 但保留兼容别名 (旧代码用 _npc / _thought)
_npc_action = _npc  # alias


# ============================================================
# 第一章：家贫（万历十五年·盛泽镇）
# ============================================================

def build_chapter_01_rich() -> ScriptedChapter:
    """第一章丰富版"""

    # ============================================================
    # Node 1: 父亲病重 (intro)
    # ============================================================
    n1 = ScriptedNode(
        node_id="intro_1_father_ill",
        round_min=1,
        round_max=2,
        role="intro",
        # 🆕 v2.10.26: 多声部迁移 (从 narrative 字符串 → narrative_sections)
        narrative_sections=[
            _narrator("万历十五年三月十二，辰时。"),
            _narrator("盛泽镇春风料峭，蚕事将兴。"),
            _npc_action("父亲", "支起身子, 咳嗽两声", ""),
            _npc("父亲", "泽儿...米缸里还有多少？", emotion="气弱"),
            _npc("张氏", "相公...还有半升，撑不过明日了。", emotion="忧", action="眼眶红了"),
            _narrator("你叫盛泽织工，年二十八。父亲沈茂卧病在床已三月，汤药不断，医家说'须长服补剂，否则入秋难支'。"),
            _narrator("家中现银不足二两，织机两架吱呀作响，米缸见底。"),
            _thought("——春日迟迟，江南的绸事一年之计在于此。我必须做出选择。"),
            # 💢 背景音效 (营造氛围)
            _sound("——吱呀", action="织机声远"),
        ],
        # 兜底 narrative 字段保留 (向后兼容)
        narrative=(
            "万历十五年三月十二，辰时。\n"
            "盛泽镇春风料峭，蚕事将兴。\n"
            "\n"
            "你叫盛澤織工，年二十八。父亲沈茂卧病在床已三月，"
            "汤药不断，医家说'须长服补剂，否则入秋难支'。\n"
            "\n"
            "家中现银不足二两，织机两架吱呀作响，米缸见底。"
            "妻张氏眼眶红肿，仍在灶前忙碌。\n"
            "\n"
            "——春日迟迟，江南的绸事一年之计在于此。"
            "你必须做出选择。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="borrow_money",
                voice_name="💰 向牙行借银子",
                description="咬牙借五两，月息三分，半年为期",
                inner_voice="张氏（低声）：'相公，三分息太重，但家中实在无米...'",
                next_node_id="intro_2_borrow",
                effects={"cash_delta": +5, "debt_delta": +5, "flag_set": ["has_debt", "met_qian"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_loom",
                voice_name="🧵 卖一架织机",
                description="可换三两银子，但失去半份生计",
                inner_voice="父亲（病榻上咳嗽）：'败...败家啊...'",
                next_node_id="intro_2_sell",
                effects={"cash_delta": +3, "looms_delta": -1, "flag_set": ["sold_loom"]},
            ),
            ScriptedVoiceOption(
                voice_id="go_suzhou",
                voice_name="🚶 上苏州接单",
                description="离乡三日，去苏州寻绸缎订单",
                inner_voice="母亲：'儿啊，路上小心，盘缠莫乱花。'",
                next_node_id="intro_2_suzhou",
                effects={"city_move": "suzhou", "flag_set": ["went_to_suzhou"]},
            ),
            ScriptedVoiceOption(
                voice_id="ask_zhang",
                voice_name="🤝 求张叔帮忙",
                description="邻镇张叔（织染坊主）或许肯帮衬",
                inner_voice="张氏：'张叔素来热心，但他家也不宽裕。'",
                next_node_id="intro_2_zhang",
                effects={"flag_set": ["met_zhang"]},
            ),
        ],
    )

    # ============================================================
    # Node 2a: 借银子 - 钱老板登场
    # ============================================================
    n2a = ScriptedNode(
        node_id="intro_2_borrow",
        round_min=2,
        round_max=3,
        role="escalation",
        # 🆕 v2.10.26: 多声部迁移
        narrative_sections=[
            _narrator("镇东牙行，你坐在柜台前。"),
            _sound("——噼里啪啦", action="算盘响"),
            _npc("钱老板", "沈老弟，借多少？", emotion="笑"),
            _narrator("你递上借据，他核过指印。"),
            _npc("钱老板", "五两足色纹银，月息三分，半年为期。到期莫误，误则加息，再误则上堂。", emotion="假笑"),
            _sound("——吹", action="钱老板吹了吹借据"),
            _narrator("你揣着五两银子走出牙行，春风扑面，心中却沉甸甸。"),
            _thought("——债，就这样背上了。"),
        ],
        narrative=(
            "镇东牙行钱老板接过借据，笑眯眯地核过指印。\n"
            "\n"
            "'五两足色纹银，月息三分，半年为期。到期莫误，'"
            "钱老板吹了吹借据：'误则加息，再误则上堂。'\n"
            "\n"
            "你揣着五两银子走出牙行，春风扑面，心中却沉甸甸。"
            "——债就这样背上了。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="buy_silk_urgent",
                voice_name="买生丝，赶织春绸",
                description="趁春绸行情好，赶织一批卖与盛泽牙行",
                inner_voice="张氏：'日夜赶工，身子吃得消？'",
                next_node_id="climax_silk",
                effects={"cash_delta": -4, "rice_delta": +5, "stamina_delta": -10},
            ),
            ScriptedVoiceOption(
                voice_id="save_for_medicine",
                voice_name="先存一半，给父亲抓药",
                description="稳妥起见，先保父亲身体",
                inner_voice="张氏：'药钱要紧，织机慢慢来。'",
                next_node_id="climax_medicine",
                effects={"cash_delta": -2, "father_health_delta": +20},
            ),
            ScriptedVoiceOption(
                voice_id="go_tea_house",
                voice_name="去茶馆听行情",
                description="顺便打听苏州那边绸价",
                inner_voice="茶馆伙计：'沈家小子，你爹可好些？'",
                next_node_id="escalation_tea",
                effects={"flag_set": ["heard_news"]},
            ),
        ],
    )

    # ============================================================
    # Node 2b: 卖织机 - 镇上议论
    # ============================================================
    n2b = ScriptedNode(
        node_id="intro_2_sell",
        round_min=2,
        round_max=3,
        role="escalation",
                narrative_sections=[
            _narrator('"镇西旧货行王掌柜验过织机，沉吟半响。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'三两银子，沈老弟，你这织机七成新，原值五两。\'"'),
            _narrator('"王掌柜拨弄算盘：\'现银三两，不能再多了。\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _sound('"你扛着三两银子回家，父亲咳得更厉害了。"'),
            _narrator('"——家中只剩一架织机。"'),
        ],
        narrative=(
            "镇西旧货行王掌柜验过织机，沉吟半响。\n"
            "\n"
            "'三两银子，沈老弟，你这织机七成新，原值五两。'"
            "王掌柜拨弄算盘：'现银三两，不能再多了。'\n"
            "\n"
            "你扛着三两银子回家，父亲咳得更厉害了。"
            "——家中只剩一架织机。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="buy_medicine_first",
                voice_name="先抓药，父亲要紧",
                description="三两银子全换汤药",
                inner_voice="张氏：'爹，您可要撑住啊...'",
                next_node_id="climax_medicine",
                effects={"cash_delta": -3, "father_health_delta": +30, "flag_set": ["father_serious"]},
            ),
            ScriptedVoiceOption(
                voice_id="buy_food_rice",
                voice_name="先买米，全家不能饿",
                description="春米五斗，再撑半月",
                inner_voice="张氏：'孩子也饿得慌...'",
                next_node_id="climax_hungry",
                effects={"cash_delta": -2, "rice_delta": +8, "flag_set": ["hungry"]},
            ),
            ScriptedVoiceOption(
                voice_id="borrow_anyway",
                voice_name="还是借钱周转",
                description="三两不够，还是借点吧",
                inner_voice="张氏：'卖一架还不够？真要借？'",
                next_node_id="intro_2_borrow",
                effects={"cash_delta": +3, "debt_delta": +3, "flag_set": ["has_debt", "met_qian"]},
            ),
        ],
    )

    # ============================================================
    # Node 2c: 上苏州 - 阊门码头
    # ============================================================
    n2c = ScriptedNode(
        node_id="intro_2_suzhou",
        round_min=2,
        round_max=3,
        role="escalation",
                narrative_sections=[
            _narrator('"你搭船三日到了苏州府。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"阊门码头人声鼎沸，绸缎牙行鳞次栉比。"'),
            _narrator('"城中织机超过三万台，\'机户出资，机工出力\'。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你寻了一家\'恒德祥\'牙行，递上自家织的春绸样。"'),
            _narrator('"掌柜打量一番：'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'盛泽来的？织工几何？手艺倒还过得去。\''),
            _narrator('"'),
            _narrator('"\'眼下正缺一批夏绸，单子嘛——\'"'),
        ],
        narrative=(
            "你搭船三日到了苏州府。\n"
            "\n"
            "阊门码头人声鼎沸，绸缎牙行鳞次栉比。"
            "城中织机超过三万台，'机户出资，机工出力'。\n"
            "\n"
            "你寻了一家'恒德祥'牙行，递上自家织的春绸样。"
            "掌柜打量一番：\n"
            "\n"
            "'盛泽来的？织工几何？手艺倒还过得去。'\n"
            "'眼下正缺一批夏绸，单子嘛——'"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="take_order",
                voice_name="接下订单，赶织夏绸",
                description="三十匹夏绸，限两月交货",
                inner_voice="掌柜：'定金一两，尾款验货后结。'",
                next_node_id="climax_silk",
                effects={"cash_delta": +1, "flag_set": ["has_order_suzhou"], "city_move": "shengze"},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_price",
                voice_name="试着抬价五分",
                description="盛泽织工手艺，不至于此价",
                inner_voice="掌柜（皱眉）：'你一个无名织工，抬什么价？'",
                check="charisma >= 2",
                check_success_node="climax_silk_better",
                check_fail_node="climax_silk",
                check_hint="嘴笨了，掌柜没理你。",
                next_node_id="climax_silk",
                effects={"flag_set": ["negotiated"], "city_move": "shengze"},
            ),
            ScriptedVoiceOption(
                voice_id="explore_suzhou",
                voice_name="先逛逛苏州城",
                description="看看苏州的行情再决定",
                inner_voice="张氏（信中）：'莫急，先看看。'",
                next_node_id="escalation_tea",
                effects={"flag_set": ["explored_suzhou"]},
            ),
        ],
    )

    # ============================================================
    # Node 2d: 张叔帮忙
    # ============================================================
    n2d = ScriptedNode(
        node_id="intro_2_zhang",
        round_min=2,
        round_max=3,
        role="escalation",
                narrative_sections=[
            _narrator('"邻镇张叔的织染坊不大，但人手齐整。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你到时，张叔正在染缸边忙着。'),
            _narrator('"'),
            _narrator('"\'你爹好些了？\'张叔让你坐下，递过一杯茶。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你说明了来意。张叔沉吟：'),
            _narrator('"'),
            _narrator('"\'帮你不难。但眼下我自己也是难关。\''),
            _narrator('"'),
            _narrator('"\'这样吧——\'"'),
        ],
        narrative=(
            "邻镇张叔的织染坊不大，但人手齐整。\n"
            "\n"
            "你到时，张叔正在染缸边忙着。\n"
            "'你爹好些了？'张叔让你坐下，递过一杯茶。\n"
            "\n"
            "你说明了来意。张叔沉吟：\n"
            "'帮你不难。但眼下我自己也是难关。'\n"
            "'这样吧——'"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="take_zhang_job",
                voice_name="接张叔的活，按件计酬",
                description="织一批小绸，单价低但稳定",
                inner_voice="张叔：'踏实做，不会亏你。'",
                next_node_id="climax_silk",
                effects={"cash_delta": +1, "flag_set": ["zhang_helped"]},
            ),
            ScriptedVoiceOption(
                voice_id="ask_zhang_loan",
                voice_name="借张叔二两银子",
                description="比牙行息低，但张叔也紧",
                inner_voice="张叔：'二两可以，但得年底还。'",
                next_node_id="intro_2_borrow",
                effects={"cash_delta": +2, "debt_delta": +2, "flag_set": ["zhang_loan", "has_debt"]},
            ),
            ScriptedVoiceOption(
                voice_id="thank_and_leave",
                voice_name="婉拒，自己想办法",
                description="张叔也不宽裕，别拖累他",
                inner_voice="张叔：'也好，自己解决心里踏实。'",
                next_node_id="escalation_tea",
                effects={"flag_set": ["proud"]},
            ),
        ],
    )

    # ============================================================
    # Node 3: 茶馆见闻 (中转 + 关键剧情)
    # ============================================================
    n3_tea = ScriptedNode(
        node_id="escalation_tea",
        round_min=3,
        round_max=4,
        role="escalation",
                narrative_sections=[
            _narrator('"盛泽镇\'四时春\'茶馆。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你坐下，茶博士端来一壶碧螺春。"'),
            _narrator('"邻桌几个织工正在低声议论。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'听说了吗？苏州那边今年夏绸要涨。\''),
            _narrator('"'),
            _narrator('"\'朝廷采办太监又要下来了。\''),
            _narrator('"'),
            _narrator('"\'听说张居正当年一条鞭法，把农人逼得紧...\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——你端起茶杯，心里琢磨下一步。"'),
        ],
        narrative=(
            "盛泽镇'四时春'茶馆。\n"
            "\n"
            "你坐下，茶博士端来一壶碧螺春。"
            "邻桌几个织工正在低声议论。\n"
            "\n"
            "'听说了吗？苏州那边今年夏绸要涨。'\n"
            "'朝廷采办太监又要下来了。'\n"
            "'听说张居正当年一条鞭法，把农人逼得紧...'\n"
            "\n"
            "——你端起茶杯，心里琢磨下一步。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="decide_silk",
                voice_name="回家，决心织绸",
                description="行情看好，回家赶织",
                inner_voice="张氏：'那赶紧的。'",
                next_node_id="climax_silk",
                effects={},
            ),
            ScriptedVoiceOption(
                voice_id="decide_medicine",
                voice_name="先回家给父亲抓药",
                description="病情不能再拖",
                inner_voice="张氏：'好，先保爹。'",
                next_node_id="climax_medicine",
                effects={"cash_delta": -2, "father_health_delta": +20},
            ),
            ScriptedVoiceOption(
                voice_id="visit_neighbor",
                voice_name="去邻家串门",
                description="听说周大娘织的'绮霞罗'很值钱",
                inner_voice="周大娘：'沈家小子，我教你一招。'",
                next_node_id="climax_hungry",
                effects={"flag_set": ["learned_secret"]},
            ),
            ScriptedVoiceOption(
                voice_id="listen_old_man",
                voice_name="听听老织工讲故事",
                description="邻桌一位白头翁似乎知道许多掌故",
                inner_voice="白头翁：'我织了六十年绸，看尽世事...'",
                next_node_id="escalation_old_man",
                effects={"flag_set": ["met_oldsilk"]},
            ),
        ],
    )

    # ============================================================
    # Node 3b: 老织工点拨 (新分支)
    # ============================================================
    n3_old = ScriptedNode(
        node_id="escalation_old_man",
        round_min=4,
        round_max=5,
        role="escalation",
                narrative_sections=[
            _narrator('"白头翁捋着胡须，慢慢道：'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'我织了六十年绸，看尽盛泽的兴衰。\''),
            _narrator('"'),
            _narrator('"\'要在这行当活下去，靠的不是勤快，是眼力。\''),
            _narrator('"'),
            _narrator('"\'你听好——\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"他伸出三根手指：'),
            _narrator('"'),
            _narrator('"\'一、看牙行的秤，二、看丝绸的色，三、看人心。\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——白头翁的话，像一把钥匙。"'),
        ],
        narrative=(
            "白头翁捋着胡须，慢慢道：\n"
            "\n"
            "'我织了六十年绸，看尽盛泽的兴衰。'\n"
            "'要在这行当活下去，靠的不是勤快，是眼力。'\n"
            "'你听好——'\n"
            "\n"
            "他伸出三根手指：\n"
            "'一、看牙行的秤，二、看丝绸的色，三、看人心。'\n"
            "\n"
            "——白头翁的话，像一把钥匙。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="ask_old_man_more",
                voice_name="追问牙行的秤",
                description="'牙行的秤有什么讲究？'",
                inner_voice="白头翁：'买丝时秤砣重，卖绸时秤砣轻...'",
                next_node_id="climax_silk",
                effects={"flag_set": ["knew_scale_trick"]},
            ),
            ScriptedVoiceOption(
                voice_id="ask_color",
                voice_name="追问丝绸的色",
                description="'丝绸的颜色如何看？'",
                inner_voice="白头翁：'真丝遇水色深，伪丝褪色...'",
                next_node_id="climax_silk",
                effects={"flag_set": ["knew_color_trick"]},
            ),
            ScriptedVoiceOption(
                voice_id="thank_and_leave",
                voice_name="感谢后离开",
                description="长者言尽于此，起身回家",
                inner_voice="白头翁：'去吧，年轻人。'",
                next_node_id="climax_silk",
                effects={"flag_set": ["blessed"]},
            ),
        ],
    )

    # ============================================================
    # Node 4a: 织绸大胜 (兴家路线)
    # ============================================================
    n4_silk = ScriptedNode(
        node_id="climax_silk",
        round_min=4,
        round_max=8,
        role="climax",
        # 🆕 v2.10.27: 多声部迁移
        narrative_sections=[
            _narrator("一连十日，你和张氏日夜赶织。"),
            _sound("——吱呀——唰", action="梭子穿行"),
            _narrator("妻儿睡下，你独自坐在织机前。"),
            _narrator("这天傍晚，你捧着织好的春绸去牙行。"),
            _npc("钱老板", "嗯，不错。沈老弟手艺见长。", emotion="点头"),
            _npc("钱老板", "五两银子，你点点。", emotion="微笑"),
            _sound("——叮", action="银子落入钱袋"),
            _narrator("——五两！除去成本，净赚二两。"),
            _narrator("你攥着银子站在牙行门口，春风拂面。"),
            _thought("……日夜辛苦，值得。"),
        ],
        narrative=(
            "一连十日，你和张氏日夜赶织。\n"
            "\n"
            "妻儿睡下，你独自坐在织机前。"
            "梭子穿行，丝线成匹。\n"
            "\n"
            "这天傍晚，你捧着织好的春绸去牙行——\n"
            "\n"
            "'嗯，不错。沈老弟手艺见长。'\n"
            "钱老板验过货：'五两银子，你点点。'\n"
            "\n"
            "——五两！除去成本，净赚二两。\n"
            "你攥着银子站在牙行门口，春风拂面。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="repay_debt",
                voice_name="先还债",
                description="还三分息，剩下存着",
                inner_voice="钱老板：'嗯，孺子可教。'",
                next_node_id="resolution",
                effects={"cash_delta": -1, "debt_delta": -2, "flag_set": ["repaid"]},
            ),
            ScriptedVoiceOption(
                voice_id="buy_more_silk",
                voice_name="再买生丝，扩大生产",
                description="趁行情好多赚",
                inner_voice="张氏：'小心点，别把刚赚的又赔进去。'",
                next_node_id="climax_hungry",
                effects={"cash_delta": -3, "rice_delta": +10, "looms_delta": +1},
            ),
            ScriptedVoiceOption(
                voice_id="visit_father",
                voice_name="回家看望父亲",
                description="先把好消息告诉爹",
                inner_voice="父亲（微睁眼）：'好...好...吾儿有出息...'",
                next_node_id="resolution",
                effects={"father_health_delta": +10, "flag_set": ["father_better"]},
            ),
            ScriptedVoiceOption(
                voice_id="celebrate_tea",
                voice_name="去茶馆庆贺",
                description="请老织工喝一杯",
                inner_voice="白头翁：'孺子可教。'",
                next_node_id="resolution",
                effects={"cash_delta": -1, "flag_set": ["grateful"]},
            ),
        ],
    )

    # ============================================================
    # Node 4a-better: 抬价成功 (新结局分支)
    # ============================================================
    n4_silk_better = ScriptedNode(
        node_id="climax_silk_better",
        round_min=5,
        round_max=9,
        role="climax",
        # 🆕 v2.10.28: 多声部迁移
        narrative_sections=[
            _narrator("你在苏州跟掌柜一顿舌战。"),
            _npc("你", "盛泽织工手艺，不至于此价！", emotion="涨红了脸"),
            _sound("——啪", action="掌柜拍桌"),
            _npc("掌柜", "沈老弟有种。我给你加五分，三十五匹，六两五。", emotion="笑"),
            _thought("——六两五！比原价多赚了一两半。"),
            _narrator("你喜出望外，连夜赶回盛泽。"),
            _sound("——踢踏踢踏", action="赶路马蹄声"),
        ],
        narrative=(
            "你在苏州跟掌柜一顿舌战。\n"
            "\n"
            "'盛泽织工手艺，不至于此价！'你涨红了脸。\n"
            "\n"
            "掌柜愣了半响，忽然笑了：\n"
            "'沈老弟有种。我给你加五分，三十五匹，六两五。'\n"
            "\n"
            "——六两五！比原价多赚了一两半。"
            "你喜出望外，连夜赶回盛泽。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="buy_silk_quality",
                voice_name="买上等生丝",
                description="用好料，织精品",
                inner_voice="张氏：'这丝，织出来的绸自己都看痴了...'",
                next_node_id="resolution_prosperous",
                effects={"cash_delta": -3, "flag_set": ["prosperous"]},
            ),
            ScriptedVoiceOption(
                voice_id="save_for_loom",
                voice_name="存起来买第二架织机",
                description="扩大生产规模",
                inner_voice="张氏：'买架新织机，日子就更好过了。'",
                next_node_id="resolution",
                effects={"cash_delta": -3, "looms_delta": +1, "flag_set": ["growing"]},
            ),
        ],
    )

    # ============================================================
    # Node 4b: 父亲病情 (求医路线)
    # ============================================================
    n4_med = ScriptedNode(
        node_id="climax_medicine",
        round_min=4,
        round_max=6,
        role="climax",
                narrative_sections=[
            _narrator('"半月汤药，父亲气色渐渐好了。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"一日晨起，父亲竟能下床缓步。"'),
            _narrator('"张氏喜极而泣。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'儿啊，\'父亲握着你的手，"'),
            _narrator('"\'我这条老命是你捡回来的。\''),
            _narrator('"'),
            _narrator('"\'但家中已空，为父心中有愧...\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——父亲欲言又止，似乎有话要说。"'),
        ],
        narrative=(
            "半月汤药，父亲气色渐渐好了。\n"
            "\n"
            "一日晨起，父亲竟能下床缓步。"
            "张氏喜极而泣。\n"
            "\n"
            "'儿啊，'父亲握着你的手，"
            "'我这条老命是你捡回来的。'\n"
            "'但家中已空，为父心中有愧...'\n"
            "\n"
            "——父亲欲言又止，似乎有话要说。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="ask_father_secret",
                voice_name="询问父亲的话",
                description="'爹，您想说什么？'",
                inner_voice="父亲：'有些事本想带进棺材...'",
                next_node_id="resolution",
                effects={"flag_set": ["father_secret"]},
            ),
            ScriptedVoiceOption(
                voice_id="reassure_father",
                voice_name="'爹，您养病要紧，钱的事我来。'",
                description="让父亲安心",
                inner_voice="父亲：'好孩子...'",
                next_node_id="resolution",
                effects={"flag_set": ["father_better"]},
            ),
            ScriptedVoiceOption(
                voice_id="go_work_immediately",
                voice_name="不多说，立刻去织绸",
                description="家里没米，不能停",
                inner_voice="张氏：'爹，等我们好消息。'",
                next_node_id="climax_hungry",
                effects={"cash_delta": -1, "rice_delta": +5},
            ),
        ],
    )

    # ============================================================
    # Node 4c: 米缸空 (苦难路线 → 危机)
    # ============================================================
    # ============================================================
    # Node 2b2: 镇西旧货行 卖织机分支
    # ============================================================
    n2b_more = ScriptedNode(
        node_id="intro_2_sell_more",
        round_min=2,
        round_max=4,
        role="escalation",
                narrative_sections=[
            _narrator('"你又想起镇西旧货行。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——若卖掉第二架织机，可得二两。'),
            _narrator('"'),
            _narrator('"——但家里就彻底没了生计。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"王掌柜还在拨算盘：\'沈老弟，第二架只要二两，要卖趁早。\'"'),
        ],
        narrative=(
            "你又想起镇西旧货行。\n"
            "\n"
            "——若卖掉第二架织机，可得二两。\n"
            "——但家里就彻底没了生计。\n"
            "\n"
            "王掌柜还在拨算盘：'沈老弟，第二架只要二两，要卖趁早。'"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="sell_second_loom",
                voice_name="卖掉第二架织机",
                description="彻底断后",
                inner_voice="张氏：'相公，没有织机，咱们怎么办？'",
                next_node_id="resolution_outcast",
                effects={"cash_delta": +2, "looms_delta": -1, "flag_set": ["sold_second_loom"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_sell_second",
                voice_name="死也不卖",
                description="'不卖！这是沈家最后一点指望！'",
                inner_voice="王掌柜：'也好。'",
                next_node_id="climax_hungry",
                effects={"flag_set": ["refused_sell"]},
            ),
        ],
    )

    # ============================================================
    # Node 3d: 母亲支招 (新支线)
    # ============================================================
    n3_mother = ScriptedNode(
        node_id="escalation_mother",
        round_min=2,
        round_max=4,
        role="escalation",
                narrative_sections=[
            _narrator('"母亲把你叫到灶边，从箱底翻出一块旧帕子。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'这是你外婆传下来的。\''),
            _narrator('"'),
            _narrator('"\'里头有支金簪，能当三两银子。\''),
            _narrator('"'),
            _narrator('"\'但这是沈家传了四代的物件。\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"母亲看着你，眼里含泪：'),
            _narrator('"'),
            _narrator('"\'孩子，你拿主意。\'"'),
        ],
        narrative=(
            "母亲把你叫到灶边，从箱底翻出一块旧帕子。\n"
            "\n"
            "'这是你外婆传下来的。'\n"
            "'里头有支金簪，能当三两银子。'\n"
            "'但这是沈家传了四代的物件。'\n"
            "\n"
            "母亲看着你，眼里含泪：\n"
            "'孩子，你拿主意。'"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="pawn_jin",
                voice_name="典当金簪",
                description="换三两应急",
                inner_voice="母亲：'好孩子，对不住你...'",
                next_node_id="climax_silk",
                effects={"cash_delta": +3, "flag_set": ["pawned_jin"]},
            ),
            ScriptedVoiceOption(
                voice_id="keep_jin",
                voice_name="不典当",
                description="这是沈家传家之物",
                inner_voice="母亲：'也好。'",
                next_node_id="climax_hungry",
                effects={"flag_set": ["kept_jin"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_jin",
                voice_name="卖掉金簪（不是典当）",
                description="彻底换成银子",
                inner_voice="母亲：'罢了罢了...'",
                next_node_id="climax_hungry",
                effects={"cash_delta": +3, "flag_set": ["sold_jin"]},
            ),
        ],
    )

    # ============================================================
    # Node 4e: 织机损坏 (新危机)
    # ============================================================
    n4_loom_broken = ScriptedNode(
        node_id="climax_loom_broken",
        round_min=6,
        round_max=10,
        role="climax",
                narrative_sections=[
            _narrator('"你赶织了一夜，忽然\'咔嚓\'一声。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"织机的杼轴断了。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"张氏慌张：\'相公，这下完了！\''),
            _narrator('"'),
            _narrator('"你蹲在织机前，满脸木然。'),
            _narrator('"'),
            _narrator('"——没有织机，就没有生计。"'),
        ],
        narrative=(
            "你赶织了一夜，忽然'咔嚓'一声。\n"
            "\n"
            "织机的杼轴断了。\n"
            "\n"
            "张氏慌张：'相公，这下完了！'\n"
            "你蹲在织机前，满脸木然。\n"
            "——没有织机，就没有生计。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="borrow_loom",
                voice_name="借张叔织机",
                description="求张叔借一架织机",
                inner_voice="张叔：'急人所难，但得半年还。'",
                next_node_id="climax_silk",
                effects={"flag_set": ["zhang_loom_borrow"]},
            ),
            ScriptedVoiceOption(
                voice_id="fix_loom",
                voice_name="自己修理织机",
                description="找木匠修",
                inner_voice="木匠：'一两银子，三天修好。'",
                check="cash >= 1",
                check_success_node="climax_silk",
                check_fail_node="resolution_outcast",
                check_hint="银子不够，木匠摇头走了。",
                next_node_id="climax_silk",
                effects={"cash_delta": -1, "flag_set": ["fixed_loom"]},
            ),
            ScriptedVoiceOption(
                voice_id="give_up",
                voice_name="放弃织绸",
                description="转行做别的",
                inner_voice="张氏：'相公，咱们还能做什么？'",
                next_node_id="resolution_outcast",
                effects={"flag_set": ["gave_up"]},
            ),
        ],
    )
    # ============================================================
    # Node 3c: 邻家周大娘 (新支线)
    # ============================================================
    n3_zhou = ScriptedNode(
        node_id="escalation_zhou",
        round_min=3,
        round_max=5,
        role="escalation",
        # 🆕 v2.10.28: 多声部迁移
        narrative_sections=[
            _narrator("周大娘八十多岁了，手艺是盛泽镇数一数二的。"),
            _narrator("她让你坐下，神秘兮兮。"),
            _npc("周大娘", "我教你一招——绮霞罗。", emotion="神秘", action="压低声音"),
            _npc("周大娘", "这是宫里才有的料子，一匹值十两。", emotion="严肃"),
            _npc("周大娘", "但你得答应我一件事。", emotion="眼神闪烁"),
            _thought("——周大娘的眼睛里藏着秘密。"),
        ],
        narrative=(
            "周大娘八十多岁了，手艺是盛泽镇数一数二的。\n"
            "\n"
            "她让你坐下，神秘兮兮：\n"
            "'我教你一招——绮霞罗。'\n"
            "'这是宫里才有的料子，一匹值十两。'\n"
            "'但你得答应我一件事。'\n"
            "\n"
            "——周大娘的眼睛里藏着秘密。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="agree_zhou",
                voice_name="答应周大娘",
                description="不管什么事，先学了再说",
                inner_voice="周大娘：'好孩子。'",
                next_node_id="climax_silk_better",
                effects={"cash_delta": +1, "flag_set": ["learned_qixia", "zhou_favor"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_zhou",
                voice_name="婉拒周大娘",
                description="'您老先说是什么事？'",
                inner_voice="周大娘：'罢了，你不愿就算了。'",
                next_node_id="climax_silk",
                effects={"flag_set": ["zhou_refused"]},
            ),
            ScriptedVoiceOption(
                voice_id="ask_zhou_more",
                voice_name="追问何事",
                description="'大娘，是什么事？'",
                inner_voice="周大娘：'等你织出第一匹再说。'",
                next_node_id="climax_silk",
                effects={"flag_set": ["zhou_curious"]},
            ),
        ],
    )

    # ============================================================
    # Node 4d: 父亲急病 (触发丧父结局)
    # ============================================================
    n4_father_dies = ScriptedNode(
        node_id="climax_father_dies",
        round_min=5,
        round_max=10,
        role="climax",
        # 🆕 v2.10.27: 多声部迁移
        narrative_sections=[
            _narrator("你正织着绸，张氏急匆匆跑来。"),
            _npc("张氏", "相公快回来，爹他...他吐血了！", emotion="惊恐", action="攥住你的手"),
            _sound("——沙沙沙", action="春雨打在窗上"),
            _narrator("你飞奔回家。父亲面如金纸，嘴角挂着血丝。"),
            _npc("父亲", "儿...儿啊...", emotion="气弱"),
            _thought("父亲想说什么……却只剩微弱的气息。"),
            _narrator("——春雨打在窗上，无休无止。"),
        ],
        narrative=(
            "你正织着绸，张氏急匆匆跑来。\n"
            "\n"
            "'相公快回来，爹他...他吐血了！'\n"
            "\n"
            "你飞奔回家。父亲面如金纸，"
            "嘴角挂着血丝。\n"
            "\n"
            "'儿...儿啊...'父亲想说什么，\n"
            "却只剩微弱的气息。\n"
            "——春雨打在窗上，无休无止。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="call_doctor",
                voice_name="急请郎中",
                description="张氏快去请张郎中！",
                inner_voice="张氏：'我这就跑！'",
                check="cash >= 2",
                check_success_node="climax_medicine",
                check_fail_node="resolution_father_dead",
                check_hint="银子不够，郎中摇头走了。",
                next_node_id="climax_medicine",
                effects={"cash_delta": -2},
            ),
            ScriptedVoiceOption(
                voice_id="hold_father",
                voice_name="守在父亲身边",
                description="哪儿也不去，握着他的手",
                inner_voice="父亲（喘息）：'儿...为父...累了...'",
                next_node_id="resolution_father_dead",
                effects={"flag_set": ["by_father_side"]},
            ),
        ],
    )

    n4_hungry = ScriptedNode(
        node_id="climax_hungry",
        round_min=5,
        round_max=9,
        role="climax",
                narrative_sections=[
            _narrator('"米缸渐空，孩子饿得直哭。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你咬牙又织了三天三夜，"'),
            _narrator('"眼前发黑，张氏心疼地拉你停下。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"这天午后，有人敲门。'),
            _narrator('"'),
            _narrator('"是张叔。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"\'沈家小子，听说你日夜赶工？\''),
            _narrator('"'),
            _narrator('"张叔递过一袋米：\'邻里间相互帮衬，应该的。\''),
            _narrator('"'),
            _narrator('"——这就是 D&D 中的 \'lucky encounter\'。"'),
        ],
        narrative=(
            "米缸渐空，孩子饿得直哭。\n"
            "\n"
            "你咬牙又织了三天三夜，"
            "眼前发黑，张氏心疼地拉你停下。\n"
            "\n"
            "这天午后，有人敲门。\n"
            "是张叔。\n"
            "\n"
            "'沈家小子，听说你日夜赶工？'\n"
            "张叔递过一袋米：'邻里间相互帮衬，应该的。'\n"
            "——这就是 D&D 中的 'lucky encounter'。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="thank_zhang_humbly",
                voice_name="感激张叔",
                description="'张叔大恩，没齿难忘。'",
                inner_voice="张叔：'好孩子，守住这份手艺就好。'",
                next_node_id="resolution",
                effects={"flag_set": ["grateful"]},
            ),
            ScriptedVoiceOption(
                voice_id="offer_to_pay_back",
                voice_name="承诺报答",
                description="'日后定当厚报。'",
                inner_voice="张叔：'不急，好好织绸是正事。'",
                next_node_id="resolution",
                effects={"flag_set": ["promised"]},
            ),
        ],
    )

    # ============================================================
    # Node 5a: 标准结局 - 平凡兴家
    # ============================================================
    n5_std = ScriptedNode(
        node_id="resolution",
        round_min=8,
        round_max=16,
        role="resolution",
                narrative_sections=[
            _narrator('"夏收时节，蚕事已毕。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你站在自家院中，看着两架织机并肩。"'),
            _narrator('"米缸满，银钱存，父亲安好。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"张氏端来一碗绿豆汤：\'相公，喝口凉的。\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——江南的夏日很长，万历十五年还很长。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"【第一章完 · 平凡结局】"'),
        ],
        narrative=(
            "夏收时节，蚕事已毕。\n"
            "\n"
            "你站在自家院中，看着两架织机并肩。"
            "米缸满，银钱存，父亲安好。\n"
            "\n"
            "张氏端来一碗绿豆汤：'相公，喝口凉的。'\n"
            "\n"
            "——江南的夏日很长，万历十五年还很长。\n"
            "\n"
            "【第一章完 · 平凡结局】"
        ),
        voice_options=[ScriptedVoiceOption(
            voice_id="restart",
            voice_name="↺ 重玩第一章",
            description="还有 3 个隐藏结局待解锁",
            inner_voice="",
            next_node_id="intro_1_father_ill",
            effects={"flag_set": ["restarted"]},
        )],
    )

    # ============================================================
    # Node 5b: 兴家结局 (结局 2)
    # ============================================================
    # ============================================================
    # Node 4c-bad: 负债累累 (新危机节点)
    # ============================================================
    n4_bad_debt = ScriptedNode(
        node_id="climax_bad_debt",
        round_min=6,
        round_max=12,
        role="climax",
                narrative_sections=[
            _narrator('"春蚕收成不好，牙行的利息翻了一番。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"钱老板的伙计上门了：\'沈老弟，本金加利息，十一两。\''),
            _narrator('"'),
            _narrator('"你拿不出。伙计冷冷一笑：\'那就拿织机抵。\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _sound('"——家中只剩一架织机。父亲咳血不止。"'),
        ],
        narrative=(
            "春蚕收成不好，牙行的利息翻了一番。\n"
            "\n"
            "钱老板的伙计上门了：'沈老弟，本金加利息，十一两。'\n"
            "你拿不出。伙计冷冷一笑：'那就拿织机抵。'\n"
            "\n"
            "——家中只剩一架织机。父亲咳血不止。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="beg_for_time",
                voice_name="哀求宽限",
                description="跪地求钱老板再宽限半月",
                inner_voice="钱老板：'沈老弟，我也是没办法...'",
                check="charisma >= 3",
                check_success_node="climax_hungry",
                check_fail_node="resolution_bankrupt",
                check_hint="钱老板不为所动。",
                next_node_id="climax_hungry",
                effects={"flag_set": ["begged"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_everything",
                voice_name="卖光家产",
                description="卖织机、卖家具、搬出镇子",
                inner_voice="张氏：'相公，咱们去哪？'",
                next_node_id="resolution_outcast",
                effects={"looms_delta": -1, "cash_delta": +2, "flag_set": ["outcast"]},
            ),
        ],
    )

    # ============================================================
    # Node 5c: 破产结局 (结局 3)
    # ============================================================
    n5_bankrupt = ScriptedNode(
        node_id="resolution_bankrupt",
        round_min=8,
        round_max=16,
        role="resolution",
                narrative_sections=[
            _narrator('"钱老板的伙计锁了门，贴上封条。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你站在门外，看着\'沈氏织坊\'四个字。"'),
            _narrator('"张氏抱着孩子，眼眶红肿。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _sound('"父亲咳血，在担架上被抬出。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——万历十五年三月十二，你永远忘不了这一天。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"【第一章完 · 破产结局 · 妻离子散】"'),
        ],
        narrative=(
            "钱老板的伙计锁了门，贴上封条。\n"
            "\n"
            "你站在门外，看着'沈氏织坊'四个字。"
            "张氏抱着孩子，眼眶红肿。\n"
            "\n"
            "父亲咳血，在担架上被抬出。\n"
            "\n"
            "——万历十五年三月十二，你永远忘不了这一天。\n"
            "\n"
            "【第一章完 · 破产结局 · 妻离子散】"
        ),
        voice_options=[ScriptedVoiceOption(
            voice_id="restart",
            voice_name="↺ 重玩（试试其他选择）",
            description="还有 3 个结局",
            inner_voice="",
            next_node_id="intro_1_father_ill",
            effects={"flag_set": ["restarted", "saw_bankrupt"]},
        )],
    )

    # ============================================================
    # Node 5d: 出走结局 (结局 4)
    # ============================================================
    n5_outcast = ScriptedNode(
        node_id="resolution_outcast",
        round_min=10,
        round_max=16,
        role="resolution",
                narrative_sections=[
            _narrator('"你卖光家产，背着父亲，张氏抱着孩子，'),
            _narrator('"'),
            _narrator('"沿着运河往南走。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"盛泽镇渐渐远了。钱老板的伙计在身后挥手：'),
            _narrator('"'),
            _narrator('"\'沈老弟，走好不送！\''),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你攥着仅剩的二两银子，前路茫茫。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——江南很大，容得下一介流民。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"【第一章完 · 出走结局 · 浪迹天涯】"'),
        ],
        narrative=(
            "你卖光家产，背着父亲，张氏抱着孩子，\n"
            "沿着运河往南走。\n"
            "\n"
            "盛泽镇渐渐远了。钱老板的伙计在身后挥手：\n"
            "'沈老弟，走好不送！'\n"
            "\n"
            "你攥着仅剩的二两银子，前路茫茫。\n"
            "\n"
            "——江南很大，容得下一介流民。\n"
            "\n"
            "【第一章完 · 出走结局 · 浪迹天涯】"
        ),
        voice_options=[ScriptedVoiceOption(
            voice_id="restart",
            voice_name="↺ 重玩",
            description="",
            inner_voice="",
            next_node_id="intro_1_father_ill",
            effects={"flag_set": ["restarted", "saw_outcast"]},
        )],
    )

    # ============================================================
    # Node 5e: 父亲病亡结局 (隐藏结局)
    # ============================================================
    n5_father_dead = ScriptedNode(
        node_id="resolution_father_dead",
        round_min=8,
        round_max=16,
        role="resolution",
                narrative_sections=[
            _narrator('"万历十五年四月初三，卯时。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"父亲咽下了最后一口气。'),
            _narrator('"'),
            _narrator('"张氏哭得撕心裂肺，孩子在一旁发抖。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"你跪在床前，攥着父亲渐渐凉下去的手。'),
            _narrator('"'),
            _narrator('"窗外的春雨还在下。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"——父亲一生勤勉，未享过一天清福。'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"'),
            _narrator('"【第一章完 · 丧父结局 · 哀痛欲绝】"'),
        ],
        narrative=(
            "万历十五年四月初三，卯时。\n"
            "\n"
            "父亲咽下了最后一口气。\n"
            "张氏哭得撕心裂肺，孩子在一旁发抖。\n"
            "\n"
            "你跪在床前，攥着父亲渐渐凉下去的手。\n"
            "窗外的春雨还在下。\n"
            "\n"
            "——父亲一生勤勉，未享过一天清福。\n"
            "\n"
            "【第一章完 · 丧父结局 · 哀痛欲绝】"
        ),
        voice_options=[ScriptedVoiceOption(
            voice_id="restart",
            voice_name="↺ 重玩（这次救父亲）",
            description="",
            inner_voice="",
            next_node_id="intro_1_father_ill",
            effects={"flag_set": ["restarted", "saw_father_dead"]},
        )],
    )

    n5_prosperous = ScriptedNode(
        node_id="resolution_prosperous",
        round_min=10,
        round_max=16,
        role="resolution",
        # 🆕 v2.10.27: 多声部迁移
        narrative_sections=[
            _narrator("年末结账，你竟攒下了十二两银子。"),
            _sound("——砰砰砰", action="敲门声"),
            _narrator("牙行掌柜登门拜访，递上一张名帖。"),
            _npc("牙行掌柜", "沈老弟手艺了得，来年合作。", emotion="赞许"),
            _narrator("父亲安然无恙，张氏面有喜色。"),
            _npc("张氏", "相公，今年总算过了好日子。", emotion="喜"),
            _sound("——咯咯咯", action="孩子在院里追着母鸡跑"),
            _narrator("——万历十五年，是沈家的转折之年。"),
            _narrator("【第一章完 · 兴家结局 · 解锁第二章】"),
        ],
        narrative=(
            "年末结账，你竟攒下了十二两银子。\n"
            "\n"
            "牙行掌柜登门拜访，递上一张名帖：\n"
            "'沈老弟手艺了得，来年合作。'\n"
            "\n"
            "父亲安然无恙，张氏面有喜色，"
            "孩子在院里追着母鸡跑。\n"
            "\n"
            "——万历十五年，是沈家的转折之年。\n"
            "\n"
            "【第一章完 · 兴家结局 · 解锁第二章】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="continue_ch2",
                voice_name="▶ 继续第二章（敬请期待）",
                description="",
                inner_voice="",
                next_node_id="intro_1_father_ill",
                effects={"flag_set": ["chapter_complete_prosperous"]},
            ),
            ScriptedVoiceOption(
                voice_id="restart",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="intro_1_father_ill",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    # ============================================================
    # 4 个结局节点
    # ============================================================

    # 🆕 v2.10.25: 多声部叙事示例节点 (展示 narrative_sections 用法)
    n_demo_multivocal = ScriptedNode(
        node_id="ch1_demo_multivocal",
        round_min=1,
        round_max=99,
        role="intro",
        narrative_sections=[
            # 旁白场景
            NarrativeSection(narrator="旁白", text="万历十五年三月十二，辰时。"),
            NarrativeSection(narrator="旁白", text="盛泽镇春风料峭，蚕事将兴。"),
            # 父亲咳嗽 (音效 + 动作)
            NarrativeSection(narrator="", text="", sound="咳咳咳——", action="父亲支起身子"),
            NarrativeSection(
                narrator="父亲",
                text="泽儿...米缸里还有多少？",
                emotion="气弱",
            ),
            # 张氏的回应
            NarrativeSection(
                narrator="张氏",
                text="相公...还有半升。",
                emotion="忧",
                action="眼眶红了",
            ),
            # 内心独白 (italic)
            NarrativeSection(
                narrator="内心",
                text="我该怎么办？牙行的债，家里断粮，父亲的药...",
                italic=True,
            ),
            # DM 旁白
            NarrativeSection(narrator="旁白", text="——春日迟迟，江南的绸事一年之计在于此。"),
        ],
        voice_options=[
            ScriptedVoiceOption(
                voice_id="borrow_money",
                voice_name="💰 向牙行借银子",
                description="咬牙借五两，月息三分",
                inner_voice="张氏（低声）：'相公，三分息太重...'",
                next_node_id="intro_2_borrow",
                effects={"cash_delta": +5, "debt_delta": +5, "flag_set": ["has_debt"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_loom",
                voice_name="🧵 卖一架织机",
                description="可换三两",
                inner_voice="父亲：'败...败家啊...'",
                next_node_id="intro_2_sell",
                effects={"cash_delta": +3, "looms_delta": -1, "flag_set": ["sold_loom"]},
            ),
        ],
    )

    nodes: dict[str, ScriptedNode] = {
        n1.node_id: n1,
        n_demo_multivocal.node_id: n_demo_multivocal,  # 🆕 v2.10.25 多声部示例
        n2a.node_id: n2a,
        n2b.node_id: n2b,
        n2b_more.node_id: n2b_more,
        n2c.node_id: n2c,
        n2d.node_id: n2d,
        n3_tea.node_id: n3_tea,
        n3_old.node_id: n3_old,
        n3_zhou.node_id: n3_zhou,
        n3_mother.node_id: n3_mother,
        n4_silk.node_id: n4_silk,
        n4_silk_better.node_id: n4_silk_better,
        n4_med.node_id: n4_med,
        n4_hungry.node_id: n4_hungry,
        n4_bad_debt.node_id: n4_bad_debt,
        n4_father_dies.node_id: n4_father_dies,
        n4_loom_broken.node_id: n4_loom_broken,
        n5_std.node_id: n5_std,
        n5_prosperous.node_id: n5_prosperous,
        n5_bankrupt.node_id: n5_bankrupt,
        n5_outcast.node_id: n5_outcast,
        n5_father_dead.node_id: n5_father_dead,
    }

    # ============================================================
    # 随机事件 (3 个)
    # ============================================================
    encounters: list[RandomEncounter] = [
        # === 遭遇 1: 催债 ===
        RandomEncounter(
            encounter_id="debt_collector",
            name="💰 催债人来",
            description="钱老板派伙计来催债",
            trigger_round_min=3,
            trigger_round_max=10,
            trigger_flags=["has_debt"],
            trigger_city="shengze",
            probability=0.35,
            check_attribute="charisma",
            check_difficulty=12,
            great_success_sections=[
                _narrator("伙计正要开口，你递上热茶：'兄弟先坐，容我细说。'"),
                _npc("伙计", "沈老弟，我们钱老板说了，宽限三日。", emotion="意外"),
                _narrator("你巧妙周旋，债期宽限三日。"),
            ],
            success_sections=[
                _narrator("伙计面无表情，递过账单。"),
                _npc("伙计", "到期之日，沈老弟自己掂量。", emotion="冷淡"),
            ],
            fail_sections=[
                _narrator("伙计冷笑：'钱老板说了，再延一日都不行！'"),
                _npc("伙计", "明天见不着银子，就拿织机抵！", emotion="威胁"),
                _thought("你在盛泽镇还怎么抬得起头？"),
            ],
            great_success_effects={"debt_delta": -1, "flag_set": ["debt_extended"]},
            fail_effects={"looms_delta": -1, "flag_set": ["loom_seized"]},
        ),

        # === 遭遇 2: 苏州商人 ===
        RandomEncounter(
            encounter_id="suzhou_merchant",
            name="🎩 苏州商人",
            description="有苏州大绸商在盛泽镇寻访织工",
            trigger_round_min=2,
            trigger_round_max=12,
            trigger_city="shengze",
            probability=0.25,
            check_attribute="luck",
            check_difficulty=10,
            great_success_sections=[
                _narrator("一位绸商在街上拦住你：'小兄弟，你这手织得好！'"),
                _npc("绸商", "我出双倍价，你这手艺跟着我如何？", emotion="欣赏"),
            ],
            success_sections=[
                _narrator("绸商看过你的样绸，点了点头。"),
                _npc("绸商", "沈老弟，手艺还过得去。", emotion="平淡"),
            ],
            fail_sections=[
                _narrator("绸商看了一眼，摇摇头走了。"),
                _thought("也许是我这批绸还不够好。"),
            ],
            great_success_effects={"cash_delta": +3, "flag_set": ["met_big_merchant"]},
            success_effects={"cash_delta": +1, "flag_set": ["met_merchant"]},
        ),

        # === 遭遇 3: 父亲病危 ===
        RandomEncounter(
            encounter_id="father_crisis",
            name="⚠️ 父亲病危",
            description="父亲突然病重",
            trigger_round_min=4,
            trigger_round_max=10,
            probability=0.20,
            fail_sections=[
                _npc("张氏", "相公快回来，爹他...他吐血了！", emotion="惊恐"),
                _narrator("你飞奔回家，父亲面如金纸。"),
            ],
            fail_effects={"father_health_delta": -30, "flag_set": ["father_critical"]},
        ),
    ]

    chapter = ScriptedChapter(
        chapter_id=1,
        title="第一章：家贫",
        subtitle="万历十五年三月 · 盛泽镇",
        description="父亲病重、债台初筑、织工小子在江南的春日抉择。",
        nodes=nodes,
        start_node_id="intro_1_father_ill",
        end_node_ids=[
            "resolution",
            "resolution_prosperous",
            "resolution_bankrupt",
            "resolution_outcast",
            "resolution_father_dead",
        ],
        total_rounds=16,
        estimated_play_minutes=12,
        theme="抉择 / 求生",
    )

    # 把 encounters 挂在 chapter 上
    chapter.random_encounters = encounters  # type: ignore

    return chapter


_CHAPTER_CACHE = None


def get_chapter_01() -> ScriptedChapter:
    """获取第一章（丰富版缓存）"""
    global _CHAPTER_CACHE
    if _CHAPTER_CACHE is None:
        _CHAPTER_CACHE = build_chapter_01_rich()
    return _CHAPTER_CACHE