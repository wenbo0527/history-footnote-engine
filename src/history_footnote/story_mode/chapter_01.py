"""🆕 v2.10.16 Phase 10 — 第一章剧本：家贫（盛泽镇·万历十五年）

4 节点 (intro/escalation/climax/resolution) + 20 个 voice 选项
覆盖 D&D 风格：
- flag 组合 (met_zhang, has_debt, father_died)
- city 移动 (shengze → suzhou)
- effects (cash/debt/rice/loom)

历史准确度：参考《吴江县志》《万历邸钞》《金瓶梅》丝绸业背景
"""
from __future__ import annotations

from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)


def build_chapter_01() -> ScriptedChapter:
    """第一章：家贫"""

    # ============================================================
    # Node 1: intro — 父亲病重
    # ============================================================
    n1 = ScriptedNode(
        node_id="intro_1_father_ill",
        round_min=1,
        round_max=2,
        role="intro",
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
                effects={"cash_delta": +5, "debt_delta": +5, "flag_set": ["has_debt"]},
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
    # Node 2: escalation — 抉择 (4 个 sub-nodes)
    # ============================================================
    n2a = ScriptedNode(
        node_id="intro_2_borrow",
        round_min=2,
        round_max=3,
        role="escalation",
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

    n2b = ScriptedNode(
        node_id="intro_2_sell",
        round_min=2,
        round_max=3,
        role="escalation",
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
                effects={"cash_delta": +3, "debt_delta": +3, "flag_set": ["has_debt"]},
            ),
        ],
    )

    n2c = ScriptedNode(
        node_id="intro_2_suzhou",
        round_min=2,
        round_max=3,
        role="escalation",
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
                next_node_id="climax_silk",
                effects={"flag_set": ["negotiated"], "city_move": "shengze"},
                check="charisma >= 2",
                check_success_node="climax_silk_better",
                check_fail_node="climax_silk",
                check_hint="嘴笨了，掌柜没理你。",
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

    n2d = ScriptedNode(
        node_id="intro_2_zhang",
        round_min=2,
        round_max=3,
        role="escalation",
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
    # Node 3: escalation_tea — 茶馆见闻 (中转节点)
    # ============================================================
    n3_tea = ScriptedNode(
        node_id="escalation_tea",
        round_min=3,
        round_max=4,
        role="escalation",
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
                voice_id="decide_visit_neighbor",
                voice_name="去邻家串门",
                description="听说周大娘织的'绮霞罗'很值钱",
                inner_voice="周大娘：'沈家小子，我教你一招。'",
                next_node_id="climax_hungry",
                effects={"flag_set": ["learned_secret"]},
            ),
        ],
    )

    # ============================================================
    # Node 4: climax — 决定性瞬间
    # ============================================================
    n4_silk = ScriptedNode(
        node_id="climax_silk",
        round_min=4,
        round_max=8,
        role="climax",
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
        ],
    )

    n4_med = ScriptedNode(
        node_id="climax_medicine",
        round_min=4,
        round_max=6,
        role="climax",
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

    n4_hungry = ScriptedNode(
        node_id="climax_hungry",
        round_min=5,
        round_max=9,
        role="climax",
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
    # Node 5: resolution — 章节结尾
    # ============================================================
    n5 = ScriptedNode(
        node_id="resolution",
        round_min=8,
        round_max=16,
        role="resolution",
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
            "【第一章完】\n"
            "\n"
            "下一章预告：《第二章：织染》\n"
            "——苏州恒德祥的订单能否按时交货？\n"
            "——牙行的债何时能清？\n"
            "——盛泽镇的绸市将迎来怎样的风云？"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart",
                voice_name="↺ 重玩第一章（不同选择）",
                description="尝试不同选项，体验不同结局",
                inner_voice="",
                next_node_id="intro_1_father_ill",  # 重启循环
                effects={"flag_set": ["restarted"]},
            ),
            ScriptedVoiceOption(
                voice_id="continue",
                voice_name="▶ 继续第二章（敬请期待）",
                description="《第二章：织染》剧本开发中",
                inner_voice="",
                next_node_id="intro_1_father_ill",
                effects={"flag_set": ["chapter_complete"]},
            ),
        ],
    )

    chapter = ScriptedChapter(
        chapter_id=1,
        title="第一章：家贫",
        subtitle="万历十五年三月 · 盛泽镇",
        description="父亲病重、债台初筑、织工小子在江南的春日抉择。",
        nodes={
            n1.node_id: n1,
            n2a.node_id: n2a,
            n2b.node_id: n2b,
            n2c.node_id: n2c,
            n2d.node_id: n2d,
            n3_tea.node_id: n3_tea,
            n4_silk.node_id: n4_silk,
            n4_med.node_id: n4_med,
            n4_hungry.node_id: n4_hungry,
            n5.node_id: n5,
        },
        start_node_id="intro_1_father_ill",
        end_node_ids=["resolution"],
        total_rounds=16,
        estimated_play_minutes=8,
        theme="抉择 / 求生",
    )

    return chapter


# 缓存
_CHAPTER_CACHE = None


def get_chapter_01() -> ScriptedChapter:
    """获取第一章（缓存）"""
    global _CHAPTER_CACHE
    if _CHAPTER_CACHE is None:
        _CHAPTER_CACHE = build_chapter_01()
    return _CHAPTER_CACHE