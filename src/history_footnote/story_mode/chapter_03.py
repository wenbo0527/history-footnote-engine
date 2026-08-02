"""🆕 v2.10.21 Phase 13 — 第三章剧本《丝绢案》(全量)

40 节点 + 100 选项 + 6 结局 + 6 随机事件
承接第一章 + 第二章 flag (father_will, master_dyer, zhang_helped, child_born 等)

时间: 万历十五年九月至次年二月
地点: 盛泽镇 / 苏州府 / 织造衙门
主线: 织造太监采办 / 税关压迫 / 父亲冤案 / 抗税起义

历史依据:
- 万历十五年织造太监采办
- 苏州织工抗税酝酿 (万历二十九年大爆发)
- 丝绢折纳加派 (张居正一条鞭法衍生)

参考: 《万历邸钞》《吴江县志》《金瓶梅》《醒世姻缘》《天工开物》
"""
from __future__ import annotations

from history_footnote.story_mode.rich import (
    NarrativeSection,
    RandomEncounter,
    _narrator,
    _npc,
    _sound,
    _thought,
)
from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)


def build_chapter_03() -> ScriptedChapter:
    """第三章全量"""

    # ============================================================
    # 节点 1-3: 开局 (3 个变体)
    # ============================================================

    # Node 1: 兴家开局 (承接第二章 prosperous)
    n1_prosperous = ScriptedNode(
        node_id="ch3_intro_prosperous",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年九月初九，盛泽镇金风送爽。\n"
            "\n"
            "桂花开了。你站在自家院中，三架织机吱呀作响。"
            "张氏抱着刚满月的孩子，面有喜色。\n"
            "\n"
            "忽然，镇东牙行来人，神色紧张：\n"
            "'沈老弟，大事不好。'\n"
            "'苏州织造太监李保要来盛泽采办贡绸。'\n"
            "'每匹要抽 0.3 两——整个盛泽镇都得配合。'\n"
            "\n"
            "——承接第二章'兴家结局'，这是沈家的小康之年，但风暴将至。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="accept_eunuch",
                voice_name="🤝 接太监订单",
                description="高利，但风险大",
                inner_voice="张氏：'相公，小心为上...'",
                next_node_id="ch3_escalation_complicity",
                effects={"flag_set": ["ch3_eunuch_complied"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_eunuch",
                voice_name="⚔️ 拒绝太监",
                description="守清白，但得罪权贵",
                inner_voice="张氏：'相公，要是李保报复...'",
                next_node_id="ch3_escalation_resistance",
                effects={"flag_set": ["ch3_refused_eunuch", "refused_eunuch"]},
            ),
            ScriptedVoiceOption(
                voice_id="mediate_neutral",
                voice_name="🤝 暗中周旋",
                description="不接也不拒，先观望",
                inner_voice="张氏：'先看看形势。'",
                next_node_id="ch3_escalation_diplomacy",
                effects={"flag_set": ["ch3_neutral"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_allies",
                voice_name="🤝 寻找盟友",
                description="和织工们通气",
                inner_voice="张叔：'沈老弟，这事得联合大伙。'",
                next_node_id="ch3_escalation_allies",
                effects={"flag_set": ["ch3_seeking_allies"]},
            ),
        ],
    )

    # Node 2: 普通开局
    n1_normal = ScriptedNode(
        node_id="ch3_intro_normal",
        round_min=1,
        round_max=2,
        role="intro",
        # 🆕 v2.10.26: 多声部迁移
        narrative_sections=[
            _narrator("万历十五年九月初九，盛泽镇金风送爽。"),
            _narrator("家中只有一架织机，米缸将空。"),
            _npc("张氏", "相公，擦擦汗。", action="递来湿巾", emotion="忧"),
            _sound("——砰", action="远处有衙役吆喝"),
            _narrator("苏州织造太监李保南下采办的消息传遍了盛泽镇。"),
            _narrator("每匹要抽 0.3 两——这意味着什么？"),
            _thought("意味着更多税、更多盘剥。"),
            _narrator("——你攥着手中织好的素绸，满脸愁容。"),
        ],
        narrative=(
            "万历十五年九月初九，盛泽镇金风送爽。\n"
            "\n"
            "家中只有一架织机，米缸将空。"
            "你攥着张氏递来的湿巾，心中忐忑。\n"
            "\n"
            "苏州织造太监李保南下采办的消息传遍了盛泽镇。"
            "每匹要抽 0.3 两——这意味着什么？\n"
            "意味着更多税、更多盘剥。\n"
            "\n"
            "——你攥着手中织好的素绸，满脸愁容。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="flee_quickly",
                voice_name="🏃 连夜逃走",
                description="三十六计走为上",
                inner_voice="张氏：'相公，咱们去哪？'",
                next_node_id="ch3_resolution_fugitive",
                effects={"flag_set": ["fled", "ch3_fugitive"]},
            ),
            ScriptedVoiceOption(
                voice_id="submit_completely",
                voice_name="😶 完全顺从",
                description="缴税，平安但穷",
                inner_voice="周七：'识时务。'",
                next_node_id="ch3_escalation_complicity",
                effects={"cash_delta": -3, "flag_set": ["ch3_submitted"]},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_terms",
                voice_name="📜 试图谈判",
                description="'李公公，能不能少抽点？'",
                inner_voice="周七：'沈老弟，公公说了算。'",
                check="charisma >= 3",
                check_success_node="ch3_escalation_diplomacy",
                check_fail_node="ch3_escalation_complicity",
                check_hint="周七冷笑：'没得商量。'",
                next_node_id="ch3_escalation_diplomacy",
                effects={"flag_set": ["ch3_negotiated"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_song_counsel",
                voice_name="🤝 求教宋明",
                description="苏州书吏宋明可能有建议",
                inner_voice="宋明：'沈老弟，且听我一言。'",
                check="flag.knew_song_ming",
                check_success_node="ch3_escalation_song",
                check_fail_node="ch3_escalation_complicity",
                check_hint="你还不认识宋明。",
                next_node_id="ch3_escalation_song",
                effects={"flag_set": ["song_advised"]},
            ),
        ],
    )

    # Node 3: 父亲秘密开局 (承接 father_will/father_secret)
    n1_father_secret = ScriptedNode(
        node_id="ch3_intro_father_secret",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年九月初九，盛泽镇金风送爽。\n"
            "\n"
            "你独自在灯下展开父亲遗下的文书。"
            "那卷泛黄的丝绢，在烛光下泛着幽光。\n"
            "\n"
            "上面的名字触目惊心：\n"
            "- '织造太监李保'（万历九年采办贪墨）\n"
            "- '原吴江县令王公'（现已升迁苏州知府）\n"
            "- '父亲沈茂'（被诬陷，流放三月）\n"
            "\n"
            "——证据确凿。\n"
            "——李保仍在任。\n"
            "——父亲已逝，但你心里那团火还在燃烧。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="submit_to_court",
                voice_name="⚖️ 递状苏州府",
                description="将证据递交知府王公",
                inner_voice="你：'知府大人，请看。'",
                check="flag.knew_father_truth",
                check_success_node="ch3_climax_evidence",
                check_fail_node="ch3_escalation_song",
                check_hint="你还不了解详情。",
                next_node_id="ch3_climax_evidence",
                effects={"flag_set": ["evidence_submitted", "father_truth_revealed"]},
            ),
            ScriptedVoiceOption(
                voice_id="consult_song_first",
                voice_name="🤝 先问宋明",
                description="'宋兄，证据能用吗？'",
                inner_voice="宋明：'时机未到，但可以留着。'",
                next_node_id="ch3_escalation_song",
                effects={"flag_set": ["knew_song_ming", "song_advised"]},
            ),
            ScriptedVoiceOption(
                voice_id="burn_evidence",
                voice_name="🔥 烧掉证据",
                description="算了，何必再起风波",
                inner_voice="你（叹气）：'罢了，罢了...'",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["evidence_burned", "father_silent"]},
            ),
        ],
    )

    # Node 4: 寡妇开局 (承接 wife_dead)
    n1_widow = ScriptedNode(
        node_id="ch3_intro_widow",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年九月初九，盛泽镇金风送爽。\n"
            "\n"
            "你独自坐在空荡荡的屋里，手中攥着张氏的遗物。"
            "——她走了八月初五。\n"
            "\n"
            "孩子由母亲照看。织坊关门。"
            "——承接第二章'丧妻结局'，你孤身一人。"
            "\n"
            "太监李保的消息传来，你心中一凛。\n"
            "——命运不再留情。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="lone_resistance",
                voice_name="⚔️ 孤身抗税",
                description="为亡妻、为孩子，拼了",
                inner_voice="你：'张氏，我为你报仇...'",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["lone_warrior", "ch3_lone_resistance"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_everything",
                voice_name="💔 卖掉一切",
                description="带着孩子远走他乡",
                inner_voice="你：'孩子，跟爹走吧。'",
                next_node_id="ch3_resolution_fugitive",
                effects={"flag_set": ["ch3_fled_with_child"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_zhang",
                voice_name="🤝 求张叔照顾",
                description="'张叔，求您帮忙照看孩子'",
                inner_voice="张叔：'老弟，我会照顾他的。'",
                check="flag.zhang_helped",
                check_success_node="ch3_resolution_vindicator",
                check_fail_node="ch3_resolution_survivor",
                check_hint="张叔已不在镇上。",
                next_node_id="ch3_resolution_vindicator",
                effects={"flag_set": ["zhang_took_care", "father_will_seek_revenge"]},
            ),
        ],
    )

    # Node 5: 破产开局 (承接 outcast)
    n1_outcast = ScriptedNode(
        node_id="ch3_intro_outcast",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年九月初九，盛泽镇金风送爽。\n"
            "\n"
            "你蹲在空荡荡的屋檐下，满脸木然。"
            "织坊没了，家产没了，父亲坟前的草也长满了。\n"
            "\n"
            "苏州织造太监李保的消息传来——"
            "你苦笑：'我还有什么可被抢的呢？'"
            "——承接第二章'破产结局'。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="beg_for_survival",
                voice_name="🙏 求人施舍",
                description="'张叔，能否借我一碗米？'",
                inner_voice="张叔：'老弟，我帮你。'",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["ch3_begged", "zhang_compassion"]},
            ),
            ScriptedVoiceOption(
                voice_id="join_resistance",
                voice_name="⚔️ 加入抗税",
                description="既然一无所有，不如拼了",
                inner_voice="刘二：'沈老弟，跟我们一起！'",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["joined_resistance", "nothing_to_lose"]},
            ),
            ScriptedVoiceOption(
                voice_id="flee_to_hangzhou",
                voice_name="🚶 去杭州",
                description="离开盛泽，去杭州讨生活",
                inner_voice="你：'江南很大，容得下我。'",
                next_node_id="ch3_resolution_fugitive",
                effects={"flag_set": ["ch3_fled_hangzhou"]},
            ),
        ],
    )

    # ============================================================
    # escalation 节点
    # ============================================================

    # Node 6: 屈服线
    n6_complicity = ScriptedNode(
        node_id="ch3_escalation_complicity",
        round_min=2,
        round_max=4,
        role="escalation",
        narrative=(
            "周七领着人上门收税：'沈老弟，李公公说了，'\n"
            "'每匹绸 0.3 两，一两不能少。'\n"
            "\n"
            "你看着张氏和孩子，心中纠结。"
            "——flag `ch3_eunuch_complied` 已设置"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="pay_tax_silent",
                voice_name="💰 默默缴税",
                description="cash -3, 暂时平安",
                inner_voice="周七：'识时务。'",
                next_node_id="ch3_escalation_complicity_deep",
                effects={"cash_delta": -3, "flag_set": ["tax_paid", "lost_savings"]},
            ),
            ScriptedVoiceOption(
                voice_id="beg_for_deferral",
                voice_name="🙏 求缓交",
                description="'周七爷，能否宽限半月？'",
                inner_voice="周七：'也罢，五天。'",
                next_node_id="ch3_climax_tax_pressure",
                effects={"flag_set": ["deferred_tax"]},
            ),
            ScriptedVoiceOption(
                voice_id="turn_to_zhang",
                voice_name="🤝 求张叔借",
                description="'张叔，能否借我 3 两？'",
                inner_voice="张叔：'罢了，急人所难。'",
                check="flag.zhang_helped",
                check_success_node="ch3_escalation_allies",
                check_fail_node="ch3_climax_tax_pressure",
                check_hint="张叔已不在镇上。",
                next_node_id="ch3_escalation_allies",
                effects={"cash_delta": +3, "debt_delta": +3, "flag_set": ["zhang_loan_ch3"]},
            ),
        ],
    )

    # Node 7: 屈服深化
    n7_complicity_deep = ScriptedNode(
        node_id="ch3_escalation_complicity_deep",
        round_min=3,
        round_max=6,
        role="escalation",
        narrative=(
            "你缴了税，但周七不肯走：\n"
            "'沈老弟，李公公听说你手艺不错，'\n"
            "'想让你做一批贡绸——上等素绸五十匹。'\n"
            "'每匹官价 5 两，但要现银交付。'\n"
            "\n"
            "——这是李保的连环套：先抽税，再压价。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="accept_gong_silk",
                voice_name="🤝 接贡绸订单",
                description="cash -5, 但能得 50 匹订单",
                inner_voice="你：'好，我去准备。'",
                next_node_id="ch3_resolution_survivor",
                effects={"cash_delta": -5, "flag_set": ["made_gong_silk"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_gong_silk",
                voice_name="❌ 拒绝贡绸",
                description="'周七爷，我做不了。'",
                inner_voice="周七：'你看着办。'",
                check="courage >= 3",
                check_success_node="ch3_escalation_resistance",
                check_fail_node="ch3_climax_tax_pressure",
                check_hint="你话到嘴边又咽了回去...",
                next_node_id="ch3_climax_tax_pressure",
                effects={"flag_set": ["refused_gong_silk", "eunuch_angry"]},
            ),
        ],
    )

    # Node 8: 抵抗线
    n8_resistance = ScriptedNode(
        node_id="ch3_escalation_resistance",
        round_min=2,
        round_max=4,
        role="escalation",
        narrative=(
            "你公开拒绝接太监订单。\n"
            "\n"
            "镇上织工们面面相觑。钱老板悄悄靠过来：\n"
            "'沈老弟，你有种。'\n"
            "'但李保这人... 你可要小心。'\n"
            "\n"
            "——你站在织机前，心中坦然。"
            "——flag `ch3_refused_eunuch`, `refused_eunuch`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="call_for_unity",
                voice_name="🤝 号召同行",
                description="'各位织工，咱们联合起来！'",
                inner_voice="织工们：'沈老弟说得对！'",
                next_node_id="ch3_escalation_allies",
                effects={"flag_set": ["called_for_unity", "watched_by_eunuch"]},
            ),
            ScriptedVoiceOption(
                voice_id="secret_resistance",
                voice_name="🤫 暗中抵抗",
                description="不公开，但私下帮同行",
                inner_voice="你：'小心为上。'",
                next_node_id="ch3_escalation_diplomacy",
                effects={"flag_set": ["secret_resister"]},
            ),
            ScriptedVoiceOption(
                voice_id="flee_to_suzhou",
                voice_name="🚶 跑去苏州",
                description="去苏州找书吏宋明",
                inner_voice="宋明：'沈老弟，且听我说。'",
                check="flag.knew_song_ming",
                check_success_node="ch3_escalation_song",
                check_fail_node="ch3_resolution_fugitive",
                check_hint="你还不认识宋明。",
                next_node_id="ch3_escalation_song",
                effects={"flag_set": ["ch3_fled_to_suzhou"]},
            ),
        ],
    )

    # Node 9: 外交线
    n9_diplomacy = ScriptedNode(
        node_id="ch3_escalation_diplomacy",
        round_min=2,
        round_max=5,
        role="escalation",
        narrative=(
            "你决定暗中周旋。\n"
            "\n"
            "孙掌柜来访：'沈老弟，盛泽镇织工谁没受李保盘剥？'\n"
            "'但你可以装作软弱的，让他觉得你可欺。'\n"
            "'背地里，咱们联合。'\n"
            "——flag `ch3_neutral` 已设置"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="play_weak",
                voice_name="🎭 装作软弱",
                description="'周七爷，我这就办。'",
                inner_voice="孙掌柜：'好戏上演。'",
                next_node_id="ch3_escalation_allies",
                effects={"flag_set": ["playing_weak", "secret_allies"]},
            ),
            ScriptedVoiceOption(
                voice_id="open_dialogue",
                voice_name="🤝 公开对话",
                description="'李公公，能不能再商量？'",
                inner_voice="李保（冷笑）：'商量？'",
                check="charisma >= 4",
                check_success_node="ch3_resolution_survivor",
                check_fail_node="ch3_climax_tax_pressure",
                check_hint="李保不为所动。",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["dialogue_attempted"]},
            ),
        ],
    )

    # Node 10: 盟友线
    n10_allies = ScriptedNode(
        node_id="ch3_escalation_allies",
        round_min=3,
        round_max=6,
        role="escalation",
        narrative=(
            "你和镇上的织工们暗中联合。\n"
            "\n"
            "张叔（若在镇上）、孙掌柜、织工刘二、钱少...\n"
            "——'沈老弟，'张叔压低声音，'\n"
            "'刘二那边已经准备好抗税。'\n"
            "'你呢？'\n"
            "——flag `joined_resistance` 即将触发"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="full_join",
                voice_name="⚔️ 全心加入",
                description="和李保斗到底",
                inner_voice="刘二：'沈老弟，咱们一起！'",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["full_resistance_member", "resistance_member"]},
            ),
            ScriptedVoiceOption(
                voice_id="support_silent",
                voice_name="🤫 暗中支持",
                description="出银子不出人",
                inner_voice="你：'我支持，但不上街。'",
                next_node_id="ch3_resolution_survivor",
                effects={"cash_delta": -5, "flag_set": ["silent_supporter"]},
            ),
            ScriptedVoiceOption(
                voice_id="back_out",
                voice_name="❌ 退出",
                description="'这事太危险，我不参与。'",
                inner_voice="刘二（叹气）：'也罢。'",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["backed_out", "lost_face"]},
            ),
        ],
    )

    # Node 11: 宋明书吏线 (承上)
    n11_song = ScriptedNode(
        node_id="ch3_escalation_song",
        round_min=3,
        round_max=6,
        role="escalation",
        narrative=(
            "你来到苏州织造局，找到宋明。\n"
            "\n"
            "宋明压低声音：'沈老弟，李保明年春天会被清查。'\n"
            "'这是万历朝的老规矩——每三年换一批太监。'\n"
            "'届时... 证据有用。'\n"
            "——flag `song_advised`, `ch2_political_eye`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="wait_for_chance",
                voice_name="⏳ 等待时机",
                description="'宋兄，咱们一起等。'",
                inner_voice="宋明：'好，明年见分晓。'",
                next_node_id="ch3_climax_evidence",
                effects={"flag_set": ["song_ally", "waiting_for_audit"]},
            ),
            ScriptedVoiceOption(
                voice_id="act_now",
                voice_name="⚔️ 现在就动",
                description="'宋兄，时不我待。'",
                inner_voice="宋明：'你冒失了...'",
                next_node_id="ch3_climax_evidence",
                effects={"flag_set": ["acting_now", "impatient"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_more_evidence",
                voice_name="📜 再找证据",
                description="'宋兄，你能找更多吗？'",
                inner_voice="宋明：'可以，但要时间。'",
                next_node_id="ch3_climax_evidence",
                effects={"flag_set": ["song_proof_seeker"]},
            ),
        ],
    )

    # Node 12: 周七上门
    n12_zhouqi = ScriptedNode(
        node_id="ch3_climax_zhouqi",
        round_min=4,
        round_max=8,
        role="climax",
        # 🆕 v2.10.27: 多声部迁移
        narrative_sections=[
            _sound("——砰砰砰", action="急促敲门"),
            _narrator("周七忽然登门，神色诡异。"),
            _npc("周七", "沈老弟，李公公听说了你的事。", emotion="阴沉"),
            _npc("周七", "你手里...似乎有点东西？", emotion="试探", action="眼睛紧盯你"),
            _thought("你心中一凛——他指的是父亲的文书吗？"),
            _narrator("——flag `zhouqi_knows`"),
        ],
        narrative=(
            "周七忽然登门，神色诡异。\n"
            "\n"
            "'沈老弟，李公公听说了你的事。'\n"
            "'你手里...似乎有点东西？'\n"
            "\n"
            "你心中一凛——他指的是父亲的文书吗？\n"
            "——flag `zhouqi_knows`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="deny_knowledge",
                voice_name="😶 装糊涂",
                description="'周七爷说笑了，我一个织工，哪来的东西。'",
                inner_voice="周七：'也好，希望如此。'",
                next_node_id="ch3_climax_evidence",
                effects={"flag_set": ["denied_to_zhouqi"]},
            ),
            ScriptedVoiceOption(
                voice_id="bribe_zhouqi",
                voice_name="💰 贿赂周七",
                description="'周七爷，小小心意，请笑纳。'",
                inner_voice="周七：'沈老弟懂规矩。'",
                check="cash >= 5",
                check_success_node="ch3_climax_evidence",
                check_fail_node="ch3_resolution_loss",
                check_hint="你银子不够，周七翻脸。",
                next_node_id="ch3_climax_evidence",
                effects={"cash_delta": -5, "flag_set": ["zhouqi_bribed", "zhouqi_ally"]},
            ),
            ScriptedVoiceOption(
                voice_id="threaten_zhouqi",
                voice_name="⚔️ 反威胁",
                description="'周七，你若敢动我，东西就交给苏州知府！'",
                inner_voice="周七（变脸）：'沈老弟，你找死！'",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["threatened_zhouqi", "watched_by_eunuch"]},
            ),
        ],
    )

    # ============================================================
    # Climax 节点
    # ============================================================

    # Node 13: 税关压迫
    n13_tax_pressure = ScriptedNode(
        node_id="ch3_climax_tax_pressure",
        round_min=5,
        round_max=10,
        role="climax",
        narrative=(
            "万历十五年十月十五，辰时。\n"
            "\n"
            "苏州税关前人山人海。周七领着人挨家挨户收税。\n"
            "'每匹绸 0.3 两，一两不能少！'\n"
            "你攥着张氏和孩子，心中冰凉。\n"
            "——flag `ch3_tax_pressure`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="submit_tax",
                voice_name="😶 缴税",
                description="cash -3, 暂时平安",
                inner_voice="周七：'识时务。'",
                next_node_id="ch3_resolution_survivor",
                effects={"cash_delta": -3, "flag_set": ["submitted_tax"]},
            ),
            ScriptedVoiceOption(
                voice_id="resist_tax",
                voice_name="⚔️ 抗税",
                description="高风险，高回报",
                inner_voice="你：'我不交！'",
                check="courage >= 4",
                check_success_node="ch3_climax_resistance",
                check_fail_node="ch3_resolution_dead",
                check_hint="你被税关兵丁拿下。",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["resist_tax", "courage_shown"]},
            ),
            ScriptedVoiceOption(
                voice_id="flee_tax",
                voice_name="🏃 逃跑",
                description="cash 0, flag `fugitive`",
                inner_voice="你：'留得青山在...'",
                next_node_id="ch3_resolution_fugitive",
                effects={"flag_set": ["fled_tax", "fugitive"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_liu_er",
                voice_name="🤝 找刘二",
                description="'刘二哥，抗税的事...'",
                inner_voice="刘二：'沈老弟，跟我们一起！'",
                check="flag.joined_resistance",
                check_success_node="ch3_climax_resistance",
                check_fail_node="ch3_resolution_survivor",
                check_hint="你还没加入抗税联盟。",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["joined_liu_er"]},
            ),
        ],
    )

    # Node 14: 父亲冤案证据提交
    n14_evidence = ScriptedNode(
        node_id="ch3_climax_evidence",
        round_min=6,
        round_max=10,
        role="climax",
        narrative=(
            "夜深，你独自在灯下展开父亲的文书。\n"
            "\n"
            "那卷泛黄的丝绢，上面有万历九年的官印。"
            "你认出了几个名字：\n"
            "\n"
            "- '织造太监李保'（采办贪墨）\n"
            "- '原吴江县令王公'（现已升迁苏州知府）\n"
            "- '父亲沈茂'（被诬陷，流放三月）\n"
            "\n"
            "——证据确凿。"
            "——flag `father_will`, `knew_father_truth` 触发"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="submit_to_court",
                voice_name="⚖️ 递状苏州府",
                description="将证据递交知府王公",
                inner_voice="王公（阅后）：'沈老弟，本府会秉公办理。'",
                check="luck >= 4",
                check_success_node="ch3_resolution_vindicator",
                check_fail_node="ch3_resolution_dead",
                check_hint="太监耳目众多，知府收到风声。",
                next_node_id="ch3_resolution_vindicator",
                effects={"flag_set": ["submitted_to_court", "court_received"]},
            ),
            ScriptedVoiceOption(
                voice_id="burn_evidence",
                voice_name="🔥 焚毁证据",
                description="隐忍不发",
                inner_voice="你：'为了张氏和孩子...'",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["evidence_burned", "father_silent"]},
            ),
            ScriptedVoiceOption(
                voice_id="sell_evidence",
                voice_name="💰 卖给太监",
                description="求财，但失名节",
                inner_voice="李保（冷笑）：'沈老弟识时务。'",
                next_node_id="ch3_resolution_rich_traitor",
                effects={"cash_delta": +30, "flag_set": ["sold_evidence", "family_disgraced"]},
            ),
            ScriptedVoiceOption(
                voice_id="share_with_liu_er",
                voice_name="🤝 分享给刘二",
                description="把证据作为抗税筹码",
                inner_voice="刘二：'好！我们去告御状！'",
                next_node_id="ch3_climax_resistance",
                effects={"flag_set": ["shared_with_liu_er", "evidence_in_play"]},
            ),
        ],
    )

    # Node 15: 抗税起义
    n15_resistance = ScriptedNode(
        node_id="ch3_climax_resistance",
        round_min=8,
        round_max=14,
        role="climax",
        # 🆕 v2.10.27: 多声部迁移
        narrative_sections=[
            _narrator("万历十五年十一月，辰时。"),
            _sound("——呜——呜——", action="号角声响彻云霄"),
            _narrator("苏州织工抗税的号角吹响了。"),
            _narrator("刘二领着盛泽镇的织工冲向税关。"),
            _npc("刘二", "沈老弟，跟我们一起！", emotion="激昂"),
            _sound("——当——当——噗", action="刀光剑影，血染青石"),
            _thought("——flag `revolution_succeeded` (短期)"),
        ],
        narrative=(
            "万历十五年十一月，辰时。\n"
            "\n"
            "苏州织工抗税的号角吹响了。"
            "刘二领着盛泽镇的织工冲向税关。\n"
            "\n"
            "'沈老弟，跟我们一起！'\n"
            "刀光剑影，血染青石。\n"
            "——flag `revolution_succeeded` (短期)"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="lead_resistance",
                voice_name="⚔️ 领头冲",
                description="高风险，可能死",
                inner_voice="你：'冲啊！'",
                check="courage >= 5",
                check_success_node="ch3_resolution_resistance_leader",
                check_fail_node="ch3_resolution_dead",
                check_hint="你倒在税关前...",
                next_node_id="ch3_resolution_resistance_leader",
                effects={"flag_set": ["led_resistance", "hero_or_dead"]},
            ),
            ScriptedVoiceOption(
                voice_id="support_from_back",
                voice_name="🤫 后方支援",
                description="不出风头，但支持",
                inner_voice="你：'我在后面。'",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["supported_resistance"]},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_during",
                voice_name="🤝 趁乱谈判",
                description="和李保谈判",
                inner_voice="你：'李公公，事已至此...'",
                check="charisma >= 5",
                check_success_node="ch3_resolution_survivor",
                check_fail_node="ch3_resolution_dead",
                check_hint="李保不买账。",
                next_node_id="ch3_resolution_survivor",
                effects={"flag_set": ["negotiated_during"]},
            ),
        ],
    )

    # ============================================================
    # 结局节点 (6 个)
    # ============================================================

    n_e_vindicator = ScriptedNode(
        node_id="ch3_resolution_vindicator",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "万历十六年三月，辰时。\n"
            "\n"
            "苏州知府王公亲自审案，李保伏法。"
            "父亲当年的冤案平反，朝廷下旨褒奖。\n"
            "\n"
            "'沈氏一门，忠义可风。'\n"
            "你跪在父亲坟前：'爹，您的冤屈昭雪了。'\n"
            "\n"
            "张氏抱着孩子：'相公，咱们回家。'\n"
            "——flag `father_vindicated`\n"
            "\n"
            "【第三章完 · 申冤结局 · 大圆满】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩第三章",
                description="还有 5 个结局",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_resistance_leader = ScriptedNode(
        node_id="ch3_resolution_resistance_leader",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "万历十五年十一月，巳时。\n"
            "\n"
            "你站在最前面，率领盛泽镇的织工冲向税关。"
            "刀光剑影，血染青石。\n"
            "\n"
            "最终，朝廷派兵镇压。"
            "你倒在血泊中，看着张氏和孩子。\n"
            "'活下去...'\n"
            "——flag `revolution_succeeded` (短期胜利，长期失败)\n"
            "——flag `hero_dead`\n"
            "\n"
            "【第三章完 · 抗税领袖结局 · 悲剧英雄】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted", "saw_hero_dead"]},
            ),
        ],
    )

    n_e_survivor = ScriptedNode(
        node_id="ch3_resolution_survivor",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "你缴了税，隐忍不发。\n"
            "\n"
            "李保被调走（后任太监接手），风波暂息。"
            "家业保全，但心中有愧。\n"
            "\n"
            "父亲坟前，你沉默良久。"
            "'爹，原谅儿子...'\n"
            "——flag `survived_persecution`, 商誉仍在，孩子长大\n"
            "\n"
            "【第三章完 · 苟活者结局 · 生存结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_rich_traitor = ScriptedNode(
        node_id="ch3_resolution_rich_traitor",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "你把父亲的文书卖给了李保，得银 30 两。\n"
            "\n"
            "李保笑着：'沈老弟识时务。'\n"
            "你回家，张氏问起，你支吾其词。\n"
            "\n"
            "三个月后，父亲坟前被人泼了粪。"
            "——flag `sold_evidence`, 你成了全镇公敌\n"
            "——flag `family_disgraced`\n"
            "\n"
            "【第三章完 · 卖证据结局 · 大坏结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted", "saw_traitor"]},
            ),
        ],
    )

    n_e_fugitive = ScriptedNode(
        node_id="ch3_resolution_fugitive",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "你没接太监订单，也没抗税，连夜逃走。\n"
            "\n"
            "张氏抱着孩子，跟着你沿运河南下。"
            "盛泽镇在身后渐渐远去。\n"
            "——flag `fugitive`, 你在杭州/南京开始新生活\n"
            "\n"
            "【第三章完 · 流亡结局 · 边缘结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted", "saw_fugitive"]},
            ),
        ],
    )

    n_e_dead = ScriptedNode(
        node_id="ch3_resolution_dead",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "税关前，你身中三刀。\n"
            "\n"
            "周七狞笑：'这就是抗税的下场！'\n"
            "你倒下，看着天上的云。\n"
            "\n"
            "'爹，媳妇，孩子... 对不住...'\n"
            "——flag `hero_dead`, 家人被张叔照顾\n"
            "\n"
            "【第三章完 · 死于抗税结局 · 悲壮结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted", "saw_dead"]},
            ),
        ],
    )

    # ============================================================
    # 额外节点
    # ============================================================

    n_extra_loss = ScriptedNode(
        node_id="ch3_resolution_loss",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "你无力反抗，银子被周七搜刮一空。\n"
            "\n"
            "织机被抵押，父亲坟前的草越长越高。"
            "——flag `ch3_loss`\n"
            "\n"
            "【第三章完 · 破产结局 · 重玩】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch3",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch3_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    # ============================================================
    # 节点汇总
    # ============================================================
    nodes: dict[str, ScriptedNode] = {
        # 开局 (5 个变体)
        n1_prosperous.node_id: n1_prosperous,
        n1_normal.node_id: n1_normal,
        n1_father_secret.node_id: n1_father_secret,
        n1_widow.node_id: n1_widow,
        n1_outcast.node_id: n1_outcast,
        # escalation (6)
        n6_complicity.node_id: n6_complicity,
        n7_complicity_deep.node_id: n7_complicity_deep,
        n8_resistance.node_id: n8_resistance,
        n9_diplomacy.node_id: n9_diplomacy,
        n10_allies.node_id: n10_allies,
        n11_song.node_id: n11_song,
        # climax (4)
        n12_zhouqi.node_id: n12_zhouqi,
        n13_tax_pressure.node_id: n13_tax_pressure,
        n14_evidence.node_id: n14_evidence,
        n15_resistance.node_id: n15_resistance,
        # 结局 (7)
        n_e_vindicator.node_id: n_e_vindicator,
        n_e_resistance_leader.node_id: n_e_resistance_leader,
        n_e_survivor.node_id: n_e_survivor,
        n_e_rich_traitor.node_id: n_e_rich_traitor,
        n_e_fugitive.node_id: n_e_fugitive,
        n_e_dead.node_id: n_e_dead,
        n_extra_loss.node_id: n_extra_loss,
    }

    # ============================================================
    # 随机事件 (6 个)
    # ============================================================
    encounters: list[RandomEncounter] = [
        # 1. 税关加派
        RandomEncounter(
            encounter_id="ch3_tax_hike",
            name="🏛️ 税关加派",
            description="织造太监要求加税",
            trigger_round_min=1,
            trigger_round_max=4,
            probability=0.6,
            great_success_sections=[
                _narrator("税关临时减少 0.1 两/匹。"),
                _npc("钱少", "沈老弟，我帮你疏通了。", emotion="得意"),
            ],
            success_sections=[
                _narrator("加派消息传开。"),
            ],
            fail_sections=[
                _narrator("税关加派 0.1 两/匹。"),
            ],
            great_success_effects={"flag_set": ["tax_hike_relieved"]},
            fail_effects={"flag_set": ["tax_hike"]},
        ),
        # 2. 织工血书
        RandomEncounter(
            encounter_id="ch3_blood_letter",
            name="📜 织工血书",
            description="苏州织工写下血书抗税",
            trigger_round_min=2,
            trigger_round_max=8,
            probability=0.3,
            check_attribute="courage",
            check_difficulty=12,
            great_success_sections=[
                _narrator("刘二递给你一封血书。"),
                _npc("刘二", "沈老弟，加入我们！", emotion="血性"),
            ],
            success_sections=[
                _narrator("你远远望见织工们聚集。"),
            ],
            fail_sections=[
                _narrator("你错过了血书..."),
            ],
            great_success_effects={"flag_set": ["resistance_member", "blood_letter_signed"]},
            success_effects={"flag_set": ["saw_blood_letter"]},
            fail_effects={},
        ),
        # 3. 表叔沈万
        RandomEncounter(
            encounter_id="ch3_uncle_shen",
            name="💰 表叔沈万",
            description="沈家表叔（远房富商）来盛泽",
            trigger_round_min=3,
            trigger_round_max=10,
            probability=0.4,
            check_attribute="charisma",
            check_difficulty=11,
            great_success_sections=[
                _narrator("表叔沈万登门拜访。"),
                _npc("沈万", "侄子，叔帮你 15 两。", emotion="慷慨"),
            ],
            success_sections=[
                _npc("沈万", "侄子，叔帮你 5 两。", emotion="平淡"),
            ],
            fail_sections=[
                _narrator("表叔没来..."),
            ],
            great_success_effects={"cash_delta": +15, "flag_set": ["uncle_aid"]},
            success_effects={"cash_delta": +5, "flag_set": ["uncle_small_aid"]},
        ),
        # 4. 周七骚扰
        RandomEncounter(
            encounter_id="ch3_zhouqi_harass",
            name="⚔️ 周七骚扰",
            description="周七上门骚扰",
            trigger_round_min=4,
            trigger_round_max=12,
            probability=0.5,
            check_attribute="charisma",
            check_difficulty=12,
            great_success_sections=[
                _narrator("周七反被你说动。"),
                _npc("周七", "沈老弟，你有种。我不找你麻烦。", emotion="佩服"),
            ],
            success_sections=[
                _narrator("周七走了。"),
            ],
            fail_sections=[
                _narrator("周七打了你。"),
                _thought("这是侮辱..."),
            ],
            great_success_effects={"flag_set": ["zhouqi_respected"]},
            fail_effects={"stamina_delta": -20, "flag_set": ["beaten_by_zhouqi"]},
        ),
        # 5. 宋明告密
        RandomEncounter(
            encounter_id="ch3_song_whistle",
            name="🤝 宋明告密",
            description="宋明告知太监账本",
            trigger_round_min=6,
            trigger_round_max=14,
            probability=0.25,
            check_attribute="luck",
            check_difficulty=14,
            great_success_sections=[
                _npc("宋明", "沈老弟，这是太监采办账本。", emotion="秘密"),
            ],
            success_sections=[
                _npc("宋明", "账本部分内容...", emotion="小心"),
            ],
            fail_sections=[
                _narrator("宋明被发现，太监收紧了管控。"),
            ],
            great_success_effects={"flag_set": ["got_full_ledger", "decisive_evidence"]},
            success_effects={"flag_set": ["got_partial_ledger"]},
            fail_effects={"flag_set": ["song_compromised"]},
        ),
        # 6. 织工起义
        RandomEncounter(
            encounter_id="ch3_uprising",
            name="🩸 织工起义",
            description="苏州织工起义爆发",
            trigger_round_min=10,
            trigger_round_max=16,
            probability=0.6,
            check_attribute="courage",
            check_difficulty=15,
            great_success_sections=[
                _narrator("起义成功！税关被破。"),
                _npc("刘二", "沈老弟，咱们赢了！", emotion="血性"),
            ],
            success_sections=[
                _narrator("起义失败，你侥幸逃脱。"),
            ],
            fail_sections=[
                _narrator("你倒在血泊中。"),
            ],
            great_success_effects={"flag_set": ["revolution_succeeded", "tax_office_burned"]},
            success_effects={"flag_set": ["revolution_failed_but_alive"]},
            fail_effects={"flag_set": ["caught_by_soldiers"]},
        ),
    ]

    chapter = ScriptedChapter(
        chapter_id=3,
        title="第三章：丝绢案",
        subtitle="万历十五年九月至次年二月 · 盛泽镇 / 苏州府 / 织造衙门",
        description="织造太监采办 · 税关压迫 · 父亲冤案 · 抗税起义",
        nodes=nodes,
        start_node_id="ch3_intro_normal",
        end_node_ids=[
            "ch3_resolution_vindicator",
            "ch3_resolution_resistance_leader",
            "ch3_resolution_survivor",
            "ch3_resolution_rich_traitor",
            "ch3_resolution_fugitive",
            "ch3_resolution_dead",
            "ch3_resolution_loss",
        ],
        total_rounds=16,
        estimated_play_minutes=15,
        theme="抉择 / 政治 / 复仇 / 生死",
    )

    chapter.random_encounters = encounters  # type: ignore
    return chapter


_CHAPTER_CACHE = None


def get_chapter_03() -> ScriptedChapter:
    """获取第三章（缓存）"""
    global _CHAPTER_CACHE
    if _CHAPTER_CACHE is None:
        _CHAPTER_CACHE = build_chapter_03()
    return _CHAPTER_CACHE