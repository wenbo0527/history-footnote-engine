"""🆕 v2.10.18 Phase 12 — 第二章剧本《织染》(全量)

35 节点 + 85 选项 + 5 结局 + 5 随机事件
承接第一章 flag (has_debt, prosperous, father_secret, zhou_favor, learned_qixia 等 12 个)

时间: 万历十五年六月至九月
地点: 盛泽镇 ↔ 苏州府
主线: 苏州订单 / 家庭考验 / 织机扩张 / 父亲秘密 / 染色危机

历史依据: 万历年间江南丝绸业 + 织造太监采办前奏
"""
from __future__ import annotations

from history_footnote.story_mode.chapter_01 import _narrator, _npc, _thought
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


def build_chapter_02() -> ScriptedChapter:
    """第二章全量"""

    # ============================================================
    # 节点 1-3: 开局 (3 个变体)
    # ============================================================

    # Node 1: 兴家开局 (承接第一章 prosperous)
    n1_prosperous = ScriptedNode(
        node_id="ch2_intro_prosperous",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年六月十八，盛泽镇梅雨初歇。\n"
            "\n"
            "你站在自家院中，屋檐还挂着水珠。"
            "两架织机静默地立着，院里晒着刚织好的素绸。\n"
            "\n"
            "张氏端着姜汤出来：'相公，进屋歇歇。'"
            "'苏州恒德祥的孙掌柜又来信催了，说三十匹夏绸月底前要交。'\n"
            "\n"
            "父亲在堂屋里咳嗽了几声，但比一月前好了许多。\n"
            "——承接第一章'兴家结局'，这是沈家的小康之年。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="take_summer_order",
                voice_name="🧵 赶织苏州订单",
                description="三十匹夏绸，两月期限，净赚约 5 两",
                inner_voice="张氏：'相公，这次可得仔细了。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["ch2_take_order"]},
            ),
            ScriptedVoiceOption(
                voice_id="expand_loom",
                voice_name="🏭 扩张织坊",
                description="张叔提议合股扩大，投入 8 两，月产 7 匹",
                inner_voice="张叔：'沈老弟，机不可失。'",
                next_node_id="ch2_escalation_expand",
                effects={"cash_delta": -8, "looms_delta": +1, "flag_set": ["ch2_expand_attempt"]},
            ),
            ScriptedVoiceOption(
                voice_id="train_apprentice",
                voice_name="👨‍🏫 收个学徒",
                description="教陈家小陈学织工，月钱 1 两",
                inner_voice="陈小：'沈师傅肯收我，感激不尽！'",
                next_node_id="ch2_escalation_master",
                effects={"cash_delta": -1, "flag_set": ["ch2_apprentice"]},
            ),
            ScriptedVoiceOption(
                voice_id="family_first",
                voice_name="💑 陪伴张氏",
                description="张氏近日似有不适，找王婆看看",
                inner_voice="张氏（脸红）：'相公，没事的... 可能...有了。'",
                next_node_id="ch2_escalation_family",
                effects={"flag_set": ["wife_pregnant"]},
            ),
        ],
    )

    # Node 2: 普通开局 (默认)
    n1_normal = ScriptedNode(
        node_id="ch2_intro_normal",
        round_min=1,
        round_max=2,
        role="intro",
        # 🆕 v2.10.26: 多声部迁移
        narrative_sections=[
            _narrator("万历十五年六月十八，盛泽镇梅雨初歇。"),
            _sound("——滴答", action="屋檐滴水"),
            _narrator("家中只有一架织机，米缸将空。"),
            _npc("张氏", "相公，擦擦汗。", action="递来湿巾", emotion="忧"),
            _thought("三十匹夏绸月底前要交。家中只有一架织机……"),
            _narrator("苏州恒德祥的来信还在桌上。"),
            _narrator("若违约，牙行会扣信用；若完成，至少能还清债。"),
            _thought("——梅雨刚过，又得赶工。"),
        ],
        narrative=(
            "万历十五年六月十八，盛泽镇梅雨初歇。\n"
            "\n"
            "家中只有一架织机，米缸将空。"
            "你攥着张氏递来的湿巾，满心焦虑。\n"
            "\n"
            "苏州恒德祥的来信还在桌上，三十匹夏绸月底前要交。\n"
            "若违约，牙行会扣信用；若完成，至少能还清债。\n"
            "\n"
            "——梅雨刚过，又得赶工。"
            "\n"
            "——承接第一章 flag: 这段叙事会根据第一章结局动态调整。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="borrow_for_order",
                voice_name="💰 借钱周转",
                description="向张叔借 3 两，月息 5 分",
                inner_voice="张氏：'相公，张叔肯借吗？'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": +3, "debt_delta": +3, "flag_set": ["ch2_borrowed"]},
            ),
            ScriptedVoiceOption(
                voice_id="wait_for_sun",
                voice_name="⏳ 等晴天再开工",
                description="丝绸不能受潮，等梅雨彻底结束",
                inner_voice="张氏：'那订单怎么办？'",
                next_node_id="ch2_escalation_weave_late",
                effects={"flag_set": ["ch2_delayed"]},
            ),
            ScriptedVoiceOption(
                voice_id="help_neighbor",
                voice_name="🤝 先帮周大娘",
                description="周大娘病了，她托你帮她织两匹",
                inner_voice="周大娘：'沈家小子，我欠你一个人情。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": +1, "flag_set": ["zhou_favor", "ch2_zhou_debt"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_zhang_partnership",
                voice_name="🤝 求张叔合股",
                description="借一架张叔家的织机，分红给他",
                inner_voice="张叔：'也好，我看你手艺稳当。'",
                next_node_id="ch2_escalation_expand",
                effects={"flag_set": ["zhang_helped", "ch2_zhang_partner"]},
            ),
        ],
    )

    # Node 3: 父亲秘密开局 (承接第一章 father_secret)
    n1_father_secret = ScriptedNode(
        node_id="ch2_intro_father_secret",
        round_min=1,
        round_max=2,
        role="intro",
        narrative=(
            "万历十五年六月十八，盛泽镇梅雨初歇。\n"
            "\n"
            "父亲把你叫到床前，声音微弱：\n"
            "'儿啊，有些事为父一直瞒着你...'\n"
            "\n"
            "他颤巍巍从枕下摸出一卷泛黄的文书。\n"
            "'这是万历九年，为父给苏州织造局织一批贡绸的凭据。'\n"
            "'那年太监李保采办，贪墨了银两，把罪名推到为父头上。'\n"
            "'为父被打入大牢三月，虽最后平反，但再无力...'\n"
            "\n"
            "他握住你的手：'这卷文书，你要替为父保管好。'\n"
            "'若有朝一日...用得着。'\n"
            "\n"
            "——父亲的目光，苍老而决绝。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="ask_father_more",
                voice_name="📜 仔细询问详情",
                description="'爹，那年究竟发生了什么？'",
                inner_voice="父亲：'李保...李保这狗阉人...那年...那年...'",
                next_node_id="ch2_climax_father_secret",
                effects={"flag_set": ["father_will", "knew_father_truth"]},
            ),
            ScriptedVoiceOption(
                voice_id="reassure_father",
                voice_name="🤝 '爹，您养病要紧'",
                description="让父亲安心，不再追问",
                inner_voice="父亲：'好孩子...为父累了...'",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["father_will", "father_secret"]},
            ),
            ScriptedVoiceOption(
                voice_id="burn_evidence_now",
                voice_name="🔥 烧掉文书",
                description="这一页翻过去吧，何必再起风波",
                inner_voice="父亲（叹气）：'罢了，罢了...'",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["evidence_burned", "father_silent"]},
            ),
        ],
    )

    # ============================================================
    # 节点 4-7: escalation (订单/扩张/家庭/师傅)
    # ============================================================

    # 节点 4: 赶织夏绸
    n4_weave = ScriptedNode(
        node_id="ch2_escalation_weave",
        round_min=2,
        round_max=4,
        role="escalation",
        narrative=(
            "梅雨过后，盛泽镇的织机声又响了起来。\n"
            "\n"
            "你把素绸铺在架上，开始挑灯夜织。"
            "张氏端来茶：'相公，莫太累了。'\n"
            "\n"
            "窗外蛙声一片，远处河埠头的乌篷船在水雾中晃动。"
            "——三十匹夏绸，要赶在月底前完成。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="hire_xiao_chen",
                voice_name="👷 雇陈小帮忙",
                description="陈小是邻家少年，肯吃苦，月钱 1 两",
                inner_voice="陈小：'沈师傅，我不怕苦！'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -1, "flag_set": ["hired_xiao_chen"]},
            ),
            ScriptedVoiceOption(
                voice_id="buy_quality_silk",
                voice_name="💎 买上等生丝",
                description="苏州上等生丝，4 两/批，织出来的绸更细腻",
                inner_voice="张氏：'这丝，光泽真好。'",
                next_node_id="ch2_climax_quality",
                effects={"cash_delta": -4, "flag_set": ["bought_quality_silk"]},
            ),
            ScriptedVoiceOption(
                voice_id="dye_with_zhao",
                voice_name="🎨 找赵师傅染色",
                description="盛泽镇染色第一把好手，但脾气古怪",
                inner_voice="赵师傅：'沈老弟，你这绸料子不错。'",
                next_node_id="ch2_climax_dye",
                effects={"flag_set": ["met_zhao"]},
            ),
            ScriptedVoiceOption(
                voice_id="family_first",
                voice_name="💑 还是先陪张氏",
                description="她最近似乎不太舒服",
                inner_voice="张氏：'相公，我... 我可能有了。'",
                next_node_id="ch2_escalation_family",
                effects={"flag_set": ["wife_pregnant"]},
            ),
        ],
    )

    # 节点 5: 赶织延期 (普通开局)
    n4_weave_late = ScriptedNode(
        node_id="ch2_escalation_weave_late",
        round_min=3,
        round_max=5,
        role="escalation",
        narrative=(
            "又过了半月，你才开工。\n"
            "\n"
            "苏州恒德祥的孙掌柜已经来过两封信催货。"
            "你攥着信，满心焦虑。\n"
            "\n"
            "张氏劝道：'相公，能织多少是多少，莫太勉强。'\n"
            "——订单已经晚了半月。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="rush_weave",
                voice_name="⚡ 拼命赶织",
                description="日夜不眠，把能织的都织出来",
                inner_voice="张氏：'相公，身子要紧！'",
                next_node_id="ch2_climax_dye",
                effects={"stamina_delta": -20, "flag_set": ["rushed", "met_zhao"]},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_extension",
                voice_name="📜 求孙掌柜宽限",
                description="写信解释，请宽限半月",
                inner_voice="孙掌柜（信中）：'沈老弟，月底必须交，否则只能给八两。'",
                next_node_id="ch2_climax_dye",
                effects={"flag_set": ["ch2_negotiated", "merchant_disgraced"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_zhang_help",
                voice_name="🤝 求张叔借织机",
                description="借张叔家的织机，分红 30%",
                inner_voice="张叔：'也罢，急人所难。'",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["zhang_loom_borrow"]},
            ),
        ],
    )

    # 节点 6: 扩张织坊
    n4_expand = ScriptedNode(
        node_id="ch2_escalation_expand",
        round_min=2,
        round_max=4,
        role="escalation",
        narrative=(
            "张叔领你到镇东看了一间空着的织坊。\n"
            "\n"
            "'这坊，三架织机，月产九匹。'\n"
            "'我出五两，你出三两，合股经营。'\n"
            "'赚了五五分，亏了各担一半。'\n"
            "\n"
            "张叔看着你：'沈老弟，干不干？'\n"
            "——这是一次跃升的机会，但风险也大。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="agree_partnership",
                voice_name="🤝 同意合股",
                description="'好，张叔，咱们一起干！'",
                inner_voice="张叔：'好！我去安排。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -3, "flag_set": ["zhang_partner", "expanded"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_partnership",
                voice_name="❌ 婉拒合股",
                description="'张叔，我手头紧，不如小打小闹。'",
                inner_voice="张叔（叹气）：'也好，稳当些。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["refused_partnership"]},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_terms",
                voice_name="📝 重新谈条件",
                description="'张叔，我出 2 两，分红四六如何？'",
                inner_voice="张叔：'也罢，我让你一成。'",
                check="charisma >= 3",
                check_success_node="ch2_escalation_weave",
                check_fail_node="ch2_escalation_expand",
                check_hint="张叔摇头：'沈老弟，三架织机值八两，不能再少了。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -2, "flag_set": ["zhang_partner", "negotiated_terms"]},
            ),
        ],
    )

    # 节点 7: 收徒
    n4_master = ScriptedNode(
        node_id="ch2_escalation_master",
        round_min=2,
        round_max=4,
        role="escalation",
        narrative=(
            "陈小是邻家少年，今年十六。\n"
            "\n"
            "他跪在织机前：'沈师傅，肯收我为徒，一辈子感激！'\n"
            "\n"
            "你想了想：'我教你织工基本功，三年学成。'\n"
            "'但你得答应我两件事——'\n"
            "'一、不偷懒；二、织出来的绸要对得起买家。'\n"
            "\n"
            "陈小磕头：'徒儿记下了！'\n"
            "——这是沈家织坊传承的第一步。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="teach_basic",
                voice_name="📖 教基础功夫",
                description="慢慢教，三年学成",
                inner_voice="陈小：'我一定努力！'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["teaching_xiao_chen", "apprentice_started"]},
            ),
            ScriptedVoiceOption(
                voice_id="teach_advanced",
                voice_name="💎 教织'绮霞罗'",
                description="若第一章 flag learned_qixia，可教独门手艺",
                inner_voice="张氏：'相公，这可是沈家绝技。'",
                check="flag.learned_qixia",
                check_success_node="ch2_escalation_weave",
                check_fail_node="ch2_escalation_weave",
                check_hint="你还没学到'绮霞罗'，先教基础吧。",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["teaching_qixia", "qixia_passed"]},
            ),
            ScriptedVoiceOption(
                voice_id="refuse_apprentice",
                voice_name="❌ 婉拒陈小",
                description="'对不起，我现在没能力收徒。'",
                inner_voice="陈小（低头）：'是，沈师傅。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["refused_apprentice"]},
            ),
        ],
    )

    # 节点 8: 家庭线
    n4_family = ScriptedNode(
        node_id="ch2_escalation_family",
        round_min=3,
        round_max=5,
        role="escalation",
        narrative=(
            "王婆看过张氏的脉，笑了：\n"
            "'恭喜恭喜，是喜脉！两个月了。'\n"
            "\n"
            "张氏红着脸：'相公...'\n"
            "你又是欢喜又是愁——孩子是好消息，但生孩子要花 3 两。\n"
            "\n"
            "父亲在堂屋里咳嗽：'儿啊，这是沈家的根...'"
            "——一个新的生命即将到来。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="save_for_birth",
                voice_name="💰 攒钱备产",
                description="从订单款里扣 3 两存着",
                inner_voice="张氏：'相公，别太省了...'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -3, "flag_set": ["saved_for_birth"]},
            ),
            ScriptedVoiceOption(
                voice_id="continue_weaving",
                voice_name="🧵 先顾订单",
                description="先把订单完成，再想孩子的事",
                inner_voice="张氏：'相公小心身子。'",
                next_node_id="ch2_escalation_weave",
                effects={"stamina_delta": -10, "flag_set": ["overworked"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_mother_help",
                voice_name="🤝 求母亲帮忙",
                description="让母亲来照顾张氏",
                inner_voice="母亲：'儿啊，娘这就来。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["mother_helped"]},
            ),
        ],
    )

    # ============================================================
    # 节点 9-12: climax (染色/质量/秘密/税关前兆)
    # ============================================================

    # 节点 9: 染色危机
    n9_dye = ScriptedNode(
        node_id="ch2_climax_dye",
        round_min=5,
        round_max=8,
        role="climax",
        narrative=(
            "你把织好的素绸送到赵师傅处染色。\n"
            "\n"
            "赵师傅接过绸，眼里一亮：'好料！但这颜色...'\n"
            "他皱眉：'我近来得了一种怪病，染出来总不匀。'\n"
            "\n"
            "张氏闻声从灶房出来：'莫不是又喝多了？'\n"
            "赵师傅苦笑：'嫂子聪明。欠了酒债，心里苦。'\n"
            "\n"
            "——赵师傅的染色手艺，盛泽镇无人能及。但他若倒下了..."
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="treat_zhao",
                voice_name="🏥 请赵师傅看大夫",
                description="'赵老弟，我请你看大夫！'",
                inner_voice="赵师傅：'沈老弟，你...真的？'",
                check="charisma >= 3",
                check_success_node="ch2_climax_dye_success",
                check_fail_node="ch2_climax_dye_fail",
                check_hint="赵师傅摇头：'罢了，这点小病。'",
                next_node_id="ch2_climax_dye_success",
                effects={"cash_delta": -0.5, "flag_set": ["knew_color_master", "zhao_grateful"]},
            ),
            ScriptedVoiceOption(
                voice_id="find_suzhou_dyer",
                voice_name="🏙️ 找苏州师傅",
                description="贵 2 两，但稳妥",
                inner_voice="苏州师傅：'放心，三天交货。'",
                next_node_id="ch2_climax_quality",
                effects={"cash_delta": -2, "flag_set": ["suzhou_dyer"]},
            ),
            ScriptedVoiceOption(
                voice_id="learn_dye_myself",
                voice_name="🎨 自己学染色",
                description="看赵师傅的染料，琢磨琢磨",
                inner_voice="赵师傅：'你有心学，我就教。'",
                check="flag.knew_color_trick",
                check_success_node="ch2_climax_quality",
                check_fail_node="ch2_climax_dye_fail",
                check_hint="你不会染色，白看了一天。",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["learned_dye", "master_dyer"]},
            ),
            ScriptedVoiceOption(
                voice_id="buy_more_silk",
                voice_name="💰 重新买丝再织",
                description="放弃这一批，重新买丝 (cash -4)",
                inner_voice="张氏：'相公，来得及吗？'",
                next_node_id="ch2_climax_quality",
                effects={"cash_delta": -4, "flag_set": ["restitched"]},
            ),
        ],
    )

    # 节点 10: 染色成功
    n10_dye_success = ScriptedNode(
        node_id="ch2_climax_dye_success",
        round_min=6,
        round_max=9,
        role="climax",
        narrative=(
            "赵师傅喝了你的药，竟真的好了起来。\n"
            "\n"
            "他接过素绸，手微微颤抖。\n"
            "'沈老弟，这颜色，我用了四十年的功夫。'\n"
            "'今天，我把它传给你。'\n"
            "\n"
            "——你学会了'玄黄染色法'，这是盛泽镇不传之秘。"
            "——flag `knew_color_master`, `master_dyer`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="thank_zhao",
                voice_name="🙏 感谢赵师傅",
                description="'赵老弟，这手艺我一定不外传。'",
                inner_voice="赵师傅：'好孩子。'",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["qixia_mastered"]},
            ),
            ScriptedVoiceOption(
                voice_id="promise_zhao",
                voice_name="🍶 承诺给赵师傅养老",
                description="'您老若不嫌弃，徒弟我给您养老。'",
                inner_voice="赵师傅（眼眶红）：'好，好...'",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["zhao_adopted", "qixia_mastered"]},
            ),
        ],
    )

    # 节点 11: 染色失败
    n11_dye_fail = ScriptedNode(
        node_id="ch2_climax_dye_fail",
        round_min=6,
        round_max=9,
        role="climax",
        narrative=(
            "赵师傅染坏了 3 匹绸，颜色深浅不一。\n"
            "\n"
            "他满脸愧疚：'沈老弟，对不起...'\n"
            "你攥着染坏的绸，心中发凉。\n"
            "\n"
            "——苏州订单的尾款扣了一半。\n"
            "——flag `dye_failed`, `cash_delta=-3`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="accept_loss",
                voice_name="😔 接受损失",
                description="赵师傅也不容易，不追究了",
                inner_voice="赵师傅：'沈老弟大恩。'",
                next_node_id="ch2_climax_quality_partial",
                effects={"cash_delta": -3, "flag_set": ["dye_failed", "zhao_grateful"]},
            ),
            ScriptedVoiceOption(
                voice_id="demand_compensation",
                voice_name="💢 要求赔偿",
                description="'赵师傅，这损失您得担！'",
                inner_voice="赵师傅：'我...我赔不起...'",
                next_node_id="ch2_resolution_loss",
                effects={"flag_set": ["dye_compensation", "zhao_grudge"]},
            ),
        ],
    )

    # 节点 12: 染色成功 → 质量节点
    n12_quality = ScriptedNode(
        node_id="ch2_climax_quality",
        round_min=7,
        round_max=10,
        role="climax",
        narrative=(
            "玄黄染法，配上等生丝，三十匹夏绸终于完成。\n"
            "\n"
            "你看着那一匹匹绸：绛紫、月白、鸦青、藕荷...\n"
            "——这批绸，光泽如月，质地如云。\n"
            "\n"
            "孙掌柜在苏州恒德祥接到货，眼睛瞪大：\n"
            "'沈老弟，这批绸... 比我想象的还要好！'\n"
            "——订单大成功。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="accept_full_payment",
                voice_name="💰 收全款 12 两",
                description="三十匹夏绸，净赚 5 两",
                inner_voice="张氏：'相公，发财了！'",
                next_node_id="ch2_resolution_prosperous",
                effects={"cash_delta": +12, "flag_set": ["ch2_prosperous", "chapter_complete_prosperous"]},
            ),
            ScriptedVoiceOption(
                voice_id="negotiate_higher",
                voice_name="📈 试着抬价",
                description="'孙掌柜，这批值十五两。'",
                inner_voice="孙掌柜：'也罢，念你手艺，加三两。'",
                check="charisma >= 3",
                check_success_node="ch2_resolution_prosperous",
                check_fail_node="ch2_resolution_normal",
                check_hint="孙掌柜摇头：'老价钱，不能再加。'",
                next_node_id="ch2_resolution_prosperous",
                effects={"cash_delta": +15, "flag_set": ["ch2_prosperous_extra", "chapter_complete_prosperous"]},
            ),
            ScriptedVoiceOption(
                voice_id="take_gift",
                voice_name="🎁 收额外礼物",
                description="孙掌柜额外送了一匹苏州花罗",
                inner_voice="张氏：'这花罗，值五两！'",
                next_node_id="ch2_resolution_prosperous",
                effects={"cash_delta": +5, "flag_set": ["ch2_gift"]},
            ),
        ],
    )

    # 节点 13: 染色成功 → 部分完成 (次优)
    n13_quality_partial = ScriptedNode(
        node_id="ch2_climax_quality_partial",
        round_min=7,
        round_max=10,
        role="climax",
        narrative=(
            "三十匹绸只交了二十匹，剩下的还在赶工。\n"
            "\n"
            "孙掌柜叹气：'沈老弟，这次只能算部分完成。'\n"
            "'尾款打八折。'\n"
            "\n"
            "——flag `partial_complete`, `cash_delta=8`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="accept_partial",
                voice_name="😔 接受八折",
                description="保商誉要紧",
                inner_voice="孙掌柜：'下次再努力。'",
                next_node_id="ch2_resolution_normal",
                effects={"cash_delta": +8, "flag_set": ["partial_complete", "merchant_disgraced"]},
            ),
            ScriptedVoiceOption(
                voice_id="appeal_to_court",
                voice_name="⚖️ 上衙门理论",
                description="'孙掌柜，这违约是赵师傅的问题，不是我的！'",
                inner_voice="孙掌柜：'你去衙门告我？随你。'",
                next_node_id="ch2_resolution_loss",
                effects={"flag_set": ["court_attempted", "merchant_disgraced"]},
            ),
        ],
    )

    # 节点 14: 父亲秘密节点 (承接 ch2_intro_father_secret)
    n14_father_secret = ScriptedNode(
        node_id="ch2_climax_father_secret",
        round_min=2,
        round_max=4,
        role="climax",
        narrative=(
            "你展开父亲递来的文书。\n"
            "\n"
            "那是一卷泛黄的丝绢，上面有万历九年的官印。"
            "你认出了几个名字：\n"
            "\n"
            "- '织造太监李保'（采办贪墨）\n"
            "- '原吴江县令王公'（现已升迁苏州知府）\n"
            "- '父亲沈茂'（被诬陷，流放三月）\n"
            "\n"
            "——证据确凿。\n"
            "——万历十五年，李保仍在任。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="keep_evidence_safely",
                voice_name="📜 妥善保管证据",
                description="藏在织机下的暗格里",
                inner_voice="父亲：'好孩子，记住，机会会来的...'",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["evidence_kept", "father_will"]},
            ),
            ScriptedVoiceOption(
                voice_id="consult_song_ming",
                voice_name="🤝 找苏州书吏宋明",
                description="他在织造局做事，可能有用",
                inner_voice="父亲：'此人...我看他不坏。'",
                check="flag.zhou_favor",
                check_success_node="ch2_escalation_song",
                check_fail_node="ch2_intro_normal",
                check_hint="你还没认识宋明，先收好证据。",
                next_node_id="ch2_escalation_song",
                effects={"flag_set": ["knew_song_ming"]},
            ),
            ScriptedVoiceOption(
                voice_id="burn_evidence",
                voice_name="🔥 烧掉证据",
                description="不想再起风波",
                inner_voice="父亲（叹气）：'罢了，罢了...'",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["evidence_burned", "father_silent"]},
            ),
        ],
    )

    # 节点 15: 宋明书吏线 (承上)
    n15_song = ScriptedNode(
        node_id="ch2_escalation_song",
        round_min=3,
        round_max=5,
        role="escalation",
        narrative=(
            "你托周大娘的关系，认识了苏州书吏宋明。\n"
            "\n"
            "宋明在苏州织造局做书吏十年，看尽宦海沉浮。\n"
            "'沈老弟，李保这个人，我比你清楚。'\n"
            "'但眼下你动不了他——他在宫里有人。'\n"
            "\n"
            "他压低声音：'不过，明年春天朝廷会清查织造局。'\n"
            "'届时... 证据有用。'\n"
            "——flag `knew_song_ming`, `ch2_political_eye`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="trust_song",
                voice_name="🤝 信任宋明",
                description="'宋兄，咱们一起等。'",
                inner_voice="宋明：'好。明年见分晓。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["song_ally"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_more_proof",
                voice_name="📜 让宋明帮你搜集证据",
                description="'宋兄，你能找到更多证据吗？'",
                inner_voice="宋明：'可以，但要花时间。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["song_proof_seeker"]},
            ),
            ScriptedVoiceOption(
                voice_id="go_alone",
                voice_name="🚶 自己干",
                description="'宋兄，多谢指点，我自己来。'",
                inner_voice="宋明：'也好，小心为上。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["independent"]},
            ),
        ],
    )

    # ============================================================
    # 节点 16-18: 税关前兆 (太监采办伏笔)
    # ============================================================

    # 节点 16: 苏州商人传话
    n16_suzhou_news = ScriptedNode(
        node_id="ch2_escalation_suzhou_news",
        round_min=6,
        round_max=9,
        role="escalation",
        narrative=(
            "苏州恒德祥孙掌柜来访，神色紧张。\n"
            "\n"
            "'沈老弟，大事不好。'\n"
            "'苏州织造太监李保要来盛泽采办贡绸。'\n"
            "'听说每匹要抽 0.3 两——我们做买卖的，得提防。'\n"
            "\n"
            "——太监采办的前兆已经显现。"
            "——flag `ch2_heard_eunuch`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="prepare_resistance",
                voice_name="⚔️ 暗中准备",
                description="和织工们通气，不接太监订单",
                inner_voice="孙掌柜：'好，我陪你。'",
                next_node_id="ch2_climax_eunuch_arrives",
                effects={"flag_set": ["ch2_resistance_prepared"]},
            ),
            ScriptedVoiceOption(
                voice_id="comply_quietly",
                voice_name="😶 默默顺从",
                description="'孙掌柜，小心为上，先静观。'",
                inner_voice="孙掌柜：'也对，风头紧。'",
                next_node_id="ch2_climax_eunuch_arrives",
                effects={"flag_set": ["ch2_compliant"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_profit",
                voice_name="💰 趁机赚一笔",
                description="'孙掌柜，太监订单可是大买卖！'",
                inner_voice="孙掌柜（皱眉）：'你小心。'",
                next_node_id="ch2_climax_eunuch_arrives",
                effects={"flag_set": ["ch2_seek_profit"]},
            ),
        ],
    )

    # 节点 17: 太监采办抵达 (承上)
    n17_eunuch = ScriptedNode(
        node_id="ch2_climax_eunuch_arrives",
        round_min=8,
        round_max=12,
        role="climax",
        narrative=(
            "万历十五年九月初三，辰时。\n"
            "\n"
            "盛泽镇东河埠头驶来一条官船，挂着苏州织造局的旗号。\n"
            "太监李保的爪牙周七第一个上岸：\n"
            "\n"
            "'传李公公的话——盛泽镇织工，三日内献上等素绸五十匹。'\n"
            "'每匹官价 3 两，少一匹都不行！'\n"
            "\n"
            "镇上织工面面相觑，牙行钱老板悄悄靠过来：\n"
            "'沈老弟，这...这是强买强卖啊。'\n"
            "——flag `eunuch_arrived`, 第二章高潮"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="refuse_publicly",
                voice_name="⚔️ 公开拒绝",
                description="'周七，我们不接这订单！'",
                inner_voice="周七（阴笑）：'沈老弟，你有种。'",
                check="courage >= 3",
                check_success_node="ch2_resolution_prosperous",
                check_fail_node="ch2_resolution_loss",
                check_hint="你话到嘴边又咽了回去...",
                next_node_id="ch2_resolution_loss",
                effects={"flag_set": ["refused_eunuch", "watched_by_eunuch"]},
            ),
            ScriptedVoiceOption(
                voice_id="comply_secretly",
                voice_name="😶 暗中顺从",
                description="'好，我们这就准备。'",
                inner_voice="周七：'识时务。'",
                next_node_id="ch2_resolution_normal",
                effects={"cash_delta": -2, "flag_set": ["eunuch_complied"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_zhang_counsel",
                voice_name="🤝 求教张叔",
                description="'张叔，您怎么看？'",
                inner_voice="张叔：'这事得联合大伙。'",
                next_node_id="ch2_resolution_normal",
                effects={"flag_set": ["zhang_counseled", "zhang_partner"]},
            ),
        ],
    )

    # 节点 18: 周七上门催债 (伏笔 第三章)
    n18_zhouqi = ScriptedNode(
        node_id="ch2_climax_zhouqi",
        round_min=9,
        round_max=12,
        role="climax",
        narrative=(
            "周七忽然登门拜访，神色诡异。\n"
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
                next_node_id="ch2_resolution_normal",
                effects={"flag_set": ["denied_to_zhouqi"]},
            ),
            ScriptedVoiceOption(
                voice_id="bribe_zhouqi",
                voice_name="💰 贿赂周七",
                description="'周七爷，小小心意，请笑纳。'",
                inner_voice="周七：'沈老弟懂规矩。'",
                check="cash >= 5",
                check_success_node="ch2_resolution_normal",
                check_fail_node="ch2_resolution_loss",
                check_hint="你银子不够，周七翻脸。",
                next_node_id="ch2_resolution_normal",
                effects={"cash_delta": -5, "flag_set": ["zhouqi_bribed", "zhouqi_ally"]},
            ),
            ScriptedVoiceOption(
                voice_id="threaten_zhouqi",
                voice_name="⚔️ 反威胁",
                description="'周七，你若敢动我，东西就交给苏州知府！'",
                inner_voice="周七（变脸）：'沈老弟，你找死！'",
                next_node_id="ch2_resolution_loss",
                effects={"flag_set": ["threatened_zhouqi", "watched_by_eunuch"]},
            ),
        ],
    )

    # ============================================================
    # 节点 19-20: 难产 + 妻子亡 (隐藏线)
    # ============================================================

    # 节点 18.5: 张叔合股详情 (ch2_escalation_expand 的延伸)
    n18_5_zhang_partner = ScriptedNode(
        node_id="ch2_escalation_zhang_partner",
        round_min=3,
        round_max=5,
        role="escalation",
        narrative=(
            "你和张叔合股后，开始共同经营新织坊。\n"
            "\n"
            "张叔领你看了新织坊：'这坊原本是王员外的，'\n"
            "'他欠债跑了，留下三架好织机。'\n"
            "'咱俩一人出三两，加起来正好六两，能买下来。'\n"
            "\n"
            "你心中盘算：'三架织机，月产九匹。'\n"
            "'赚了五五分，亏了各担一半。'\n"
            "——这是跃升的机会。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="finalize_partnership",
                voice_name="🤝 正式合股",
                description="'张叔，咱们签契书！'",
                inner_voice="张叔：'好！明日去衙门登记。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -3, "flag_set": ["zhang_partner_final", "partnership_signed"]},
            ),
            ScriptedVoiceOption(
                voice_id="keep_loom_1_only",
                voice_name="💰 只买一架",
                description="'张叔，我只要一架，三两够了。'",
                inner_voice="张叔：'也好，稳当。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -3, "flag_set": ["single_loom", "looms_delta:+1"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_third_partner",
                voice_name="👥 找第三方入股",
                description="拉陈小入伙，三人合股",
                inner_voice="张叔：'也行，但要他出得起钱。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["seeking_third_partner"]},
            ),
        ],
    )

    # 节点 8.5: 妻子怀孕 (ch2_escalation_family 后续)
    n8_5_pregnant = ScriptedNode(
        node_id="ch2_escalation_pregnant",
        round_min=4,
        round_max=6,
        role="escalation",
        narrative=(
            "万历十五年七月初五，卯时。\n"
            "\n"
            "张氏的肚子渐渐隆起。王婆叮嘱：\n"
            "'头胎要小心，不要劳累，不要生气。'\n"
            "\n"
            "你看着她，心中又喜又忧：\n"
            "——孩子是好消息，但订单呢？父亲呢？\n"
            "——家里又得花钱了。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="save_money_for_birth",
                voice_name="💰 提前攒钱",
                description="从订单款里存 3 两产费",
                inner_voice="张氏：'相公别太省了。'",
                next_node_id="ch2_escalation_weave",
                effects={"cash_delta": -3, "flag_set": ["birth_fund_ready"]},
            ),
            ScriptedVoiceOption(
                voice_id="seek_mother_care",
                voice_name="🤝 母亲来照顾",
                description="让母亲搬来同住",
                inner_voice="母亲：'娘这就来。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["mother_moved_in", "family_support"]},
            ),
            ScriptedVoiceOption(
                voice_id="neglect_for_business",
                voice_name="💼 顾生意为主",
                description="订单要紧，顾不上张氏",
                inner_voice="张氏（低头）：'相公...'",
                next_node_id="ch2_climax_birth",
                effects={"stamina_delta": -10, "flag_set": ["neglected_wife", "bitter_wife"]},
            ),
        ],
    )

    # 节点 18.6: 苏州大订单竞争
    n18_6_suzhou_compete = ScriptedNode(
        node_id="ch2_escalation_suzhou_compete",
        round_min=7,
        round_max=10,
        role="escalation",
        narrative=(
            "苏州恒德祥孙掌柜来访，面色凝重：\n"
            "\n"
            "'沈老弟，盛泽镇今年夏绸行情紧俏。'\n"
            "'我手里有一笔大单——五十匹上等素绸。'\n"
            "'但有三四家织工争，你得表现出诚意。'\n"
            "\n"
            "他压低声音：'定金一两，但若你报价比别人低一成...'\n"
            "'我优先给你。'"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="low_bid_for_order",
                voice_name="💰 压价抢单",
                description="每匹少赚 0.3 两，但拿到订单",
                inner_voice="孙掌柜：'好，我记下了。'",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["low_bidder", "big_order_secured"]},
            ),
            ScriptedVoiceOption(
                voice_id="fair_bid",
                voice_name="📜 公道出价",
                description="'孙掌柜，我不出贱价，但手艺保证。'",
                inner_voice="孙掌柜：'也好，公平竞争。'",
                check="charisma >= 3",
                check_success_node="ch2_climax_quality",
                check_fail_node="ch2_resolution_normal",
                check_hint="孙掌柜摇头：'沈老弟，价高者得。'",
                next_node_id="ch2_climax_quality",
                effects={"flag_set": ["fair_bidder"]},
            ),
            ScriptedVoiceOption(
                voice_id="decline_order",
                voice_name="❌ 放弃这单",
                description="'孙掌柜，我手上的三十匹还没做完。'",
                inner_voice="孙掌柜（叹气）：'也好。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["declined_big_order"]},
            ),
        ],
    )

    # 节点 18.7: 学徒线深入
    n18_7_apprentice = ScriptedNode(
        node_id="ch2_escalation_apprentice",
        round_min=4,
        round_max=7,
        role="escalation",
        narrative=(
            "陈小跟了你三个月，已经能独立织素绸了。\n"
            "\n"
            "这天他红着脸来找你：'沈师傅，我想学织'绮霞罗'。'\n"
            "'那是宫里才有的料子，一匹值十两！'\n"
            "你心中一紧——这可是周大娘的绝技。\n"
            "\n"
            "——陈小的野心不小。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="teach_qixia",
                voice_name="💎 教他绮霞罗",
                description="若第一章 flag learned_qixia，可教独门手艺",
                inner_voice="陈小：'沈师傅大恩！'",
                check="flag.learned_qixia",
                check_success_node="ch2_escalation_weave",
                check_fail_node="ch2_escalation_weave",
                check_hint="你自己还没学到，先教基础吧。",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["qixia_passed", "master_dyer"]},
            ),
            ScriptedVoiceOption(
                voice_id="warn_xiao_chen",
                voice_name="⚠️ 警告陈小",
                description="'陈小，先把基础打牢。'",
                inner_voice="陈小（低头）：'是，沈师傅。'",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["warned_xiao_chen"]},
            ),
            ScriptedVoiceOption(
                voice_id="send_to_zhou",
                voice_name="🤝 让陈小拜周大娘",
                description="'你想学，去问周大娘。'",
                inner_voice="周大娘：'沈老弟，我欠你人情，教就教。'",
                check="flag.zhou_favor",
                check_success_node="ch2_escalation_weave",
                check_fail_node="ch2_escalation_weave",
                check_hint="你还没攒够周大娘的人情。",
                next_node_id="ch2_escalation_weave",
                effects={"flag_set": ["xiao_chen_to_zhou", "qixia_passed"]},
            ),
        ],
    )

    # 节点 18.8: 父亲弥留 (承接 father_secret 深度)
    n18_8_father_dying = ScriptedNode(
        node_id="ch2_climax_father_dying",
        round_min=8,
        round_max=12,
        role="climax",
        narrative=(
            "万历十五年八月初八，卯时。\n"
            "\n"
            "父亲病危。他躺在床上，气若游丝。\n"
            "'儿啊...'他颤巍巍握住你的手。\n"
            "\n"
            "——这是沈家两代人的诀别时刻。"
            "——flag `father_dying`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="ask_father_truth",
                voice_name="📜 问父亲真相",
                description="'爹，那年究竟发生了什么？'",
                inner_voice="父亲：'李保...狗阉人...那年...那年...'",
                check="flag.father_secret",
                check_success_node="ch2_resolution_prosperous",
                check_fail_node="ch2_climax_father_secret",
                check_hint="父亲摇头：'罢了，罢了...'",
                next_node_id="ch2_climax_father_secret",
                effects={"flag_set": ["father_truth_revealed", "father_will", "knew_father_truth"]},
            ),
            ScriptedVoiceOption(
                voice_id="comfort_father",
                voice_name="🤝 安慰父亲",
                description="'爹，您养病要紧，别想那些。'",
                inner_voice="父亲：'好孩子...'",
                next_node_id="ch2_resolution_prosperous",
                effects={"flag_set": ["father_comforted", "father_will"]},
            ),
            ScriptedVoiceOption(
                voice_id="hold_father_hand",
                voice_name="🤝 紧握父亲的手",
                description="哪儿也不去，握着他的手",
                inner_voice="父亲（微弱）：'儿啊，爹累了...'",
                next_node_id="ch2_resolution_prosperous",
                effects={"flag_set": ["by_father_side"]},
            ),
        ],
    )

    # 节点 18.9: 父亲安详离世 (隐藏结局)
    n18_9_father_dead = ScriptedNode(
        node_id="ch2_resolution_father_dead",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "万历十五年八月初八，辰时。\n"
            "\n"
            "父亲咽下了最后一口气。\n"
            "\n"
            "张氏哭得撕心裂肺，你跪在床前，攥着渐渐凉下去的手。"
            "——flag `father_dead`，孤身入第三章\n"
            "\n"
            "——flag `father_secret`, `father_will` 触发第三章核心剧情\n"
            "\n"
            "【第二章完 · 丧父结局 · 隐藏结局 · 解锁第三章复仇线】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="continue_ch3_vindicator",
                voice_name="▶ 继续第三章 (复仇线)",
                description="为父亲申冤",
                inner_voice="",
                next_node_id="ch2_resolution_father_dead",
                effects={"flag_set": ["chapter_complete_father_dead"]},
            ),
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    # 节点 18.10: 织坊失火 (隐藏结局·最惨)
    n18_10_fire = ScriptedNode(
        node_id="ch2_climax_fire",
        round_min=10,
        round_max=14,
        role="climax",
        narrative=(
            "万历十五年八月二十，亥时。\n"
            "\n"
            "你在睡梦中被张氏推醒：'相公，织机着火了！'\n"
            "——火星四溅，三架织机烧得精光。"
            "\n"
            "——flag `fire_loss`, `looms=0`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="save_house",
                voice_name="🏠 救房子",
                description="先救房子，织机顾不上了",
                inner_voice="张氏：'孩子！孩子还在屋里！'",
                next_node_id="ch2_resolution_fire",
                effects={"flag_set": ["house_saved", "looms_lost"]},
            ),
            ScriptedVoiceOption(
                voice_id="save_loom",
                voice_name="🧵 抢救织机",
                description="不顾一切冲进火里救织机",
                inner_voice="邻居：'沈老弟，快出来！'",
                next_node_id="ch2_resolution_fire",
                effects={"stamina_delta": -20, "flag_set": ["loom_rescue_attempt"]},
            ),
        ],
    )

    # 节点: 织坊失火结局 (隐藏·最惨)
    n_e_fire = ScriptedNode(
        node_id="ch2_resolution_fire",
        round_min=12,
        round_max=16,
        role="resolution",
        narrative=(
            "万历十五年八月二十一，卯时。\n"
            "\n"
            "织坊烧成灰烬，三架织机化为乌有。\n"
            "张氏抱着孩子，眼眶红肿。\n"
            "你蹲在废墟前，满脸木然。\n"
            "\n"
            "——flag `ch2_fire_loss`, `looms=0`\n"
            "\n"
            "【第二章完 · 织坊焚毁结局 · 隐藏结局 · 重玩】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted", "saw_fire"]},
            ),
        ],
    )

    # 节点 19: 难产
    n19_birth = ScriptedNode(
        node_id="ch2_climax_birth",
        round_min=8,
        round_max=12,
        role="climax",
        narrative=(
            "万历十五年八月初五，卯时。\n"
            "\n"
            "张氏腹痛难忍。王婆匆匆赶到：\n"
            "'沈老弟，不好了，胎位不正！'\n"
            "'得请张郎中！要 3 两银子！'\n"
            "\n"
            "你攥着银袋，心中冰凉——家里只有 2 两。\n"
            "——flag `birth_crisis`"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="call_doctor_quickly",
                voice_name="💰 急请郎中",
                description="cash -3, 母子平安",
                inner_voice="张氏：'相公，疼...'",
                check="cash >= 3",
                check_success_node="ch2_resolution_prosperous",
                check_fail_node="ch2_resolution_widow",
                check_hint="银子不够，郎中摇头走了。",
                next_node_id="ch2_resolution_widow",
                effects={"cash_delta": -3, "flag_set": ["call_doctor", "child_born"]},
            ),
            ScriptedVoiceOption(
                voice_id="hold_wife_hand",
                voice_name="🤝 紧握她的手",
                description="哪儿也不去，握着她的手",
                inner_voice="张氏（喘息）：'相公...我们的孩子...'",
                next_node_id="ch2_resolution_widow",
                effects={"flag_set": ["by_wife_side"]},
            ),
            ScriptedVoiceOption(
                voice_id="beg_zhang_for_loan",
                voice_name="🙏 求张叔借钱",
                description="'张叔，求您借我 1 两！'",
                inner_voice="张叔：'罢了，急人所难。'",
                check="flag.zhang_helped",
                check_success_node="ch2_resolution_prosperous",
                check_fail_node="ch2_resolution_widow",
                check_hint="张叔不在镇上，没人帮忙。",
                next_node_id="ch2_resolution_widow",
                effects={"cash_delta": +1, "debt_delta": +1, "flag_set": ["zhang_loan_birth"]},
            ),
        ],
    )

    # ============================================================
    # 节点 20: 结局分支汇总节点 (解决状态)
    # ============================================================

    n20_summary = ScriptedNode(
        node_id="ch2_climax_summary",
        round_min=10,
        round_max=14,
        role="climax",
        narrative=(
            "万历十五年九月中旬，秋收已毕。\n"
            "\n"
            "你在织机前整理账目，回顾这一年的得失。\n"
            "\n"
            "窗外桂花飘香，远处河埠头的乌篷船在夕阳下晃动。\n"
            "——第二章的帷幕即将落下。"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="to_prosperous_ending",
                voice_name="💰 进入兴家结局",
                description="订单大胜·家业兴旺",
                inner_voice="",
                next_node_id="ch2_resolution_prosperous",
                effects={},
            ),
            ScriptedVoiceOption(
                voice_id="to_normal_ending",
                voice_name="📜 进入平凡结局",
                description="平稳过关·日子继续",
                inner_voice="",
                next_node_id="ch2_resolution_normal",
                effects={},
            ),
            ScriptedVoiceOption(
                voice_id="to_loss_ending",
                voice_name="💢 进入违约结局",
                description="违约负债·声誉受损",
                inner_voice="",
                next_node_id="ch2_resolution_loss",
                effects={},
            ),
            ScriptedVoiceOption(
                voice_id="to_outcast_ending",
                voice_name="💔 进入破产结局",
                description="破产负债·卖光家产",
                inner_voice="",
                next_node_id="ch2_resolution_outcast",
                effects={},
            ),
        ],
    )

    # ============================================================
    # 结局节点 (5 个)
    # ============================================================

    n_e_prosperous = ScriptedNode(
        node_id="ch2_resolution_prosperous",
        round_min=12,
        round_max=16,
        role="resolution",
        narrative=(
            "秋初结算，你交了订单，攒下了二十两。\n"
            "\n"
            "苏州恒德祥孙掌柜登门：'沈老弟手艺了得，来年继续。'\n"
            "张氏抱着孩子（已满月），面有喜色：'相公，咱们...'\n"
            "\n"
            "父亲安然无恙（若 flag father_better），或已安详离世\n"
            "（若 flag father_secret → 临终托付）。\n"
            "\n"
            "——万历十五年秋，沈家已非吴下阿蒙。\n"
            "\n"
            "【第二章完 · 兴家结局 · 解锁第三章】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="continue_ch3",
                voice_name="▶ 继续第三章《丝绢案》",
                description="太监采办·税关压迫·父亲冤案",
                inner_voice="",
                next_node_id="ch2_resolution_prosperous",  # 暂时闭环
                effects={"flag_set": ["chapter_complete_prosperous"]},
            ),
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩第二章",
                description="尝试其他结局",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_normal = ScriptedNode(
        node_id="ch2_resolution_normal",
        round_min=12,
        round_max=16,
        role="resolution",
        narrative=(
            "订单如期完成，但利润微薄。\n"
            "\n"
            "你带着十二两银子回家，松了口气。"
            "张氏端来粥：'相公，歇歇吧。'\n"
            "\n"
            "窗外桂香飘来，日子还在继续。\n"
            "\n"
            "【第二章完 · 平凡结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="continue_ch3_normal",
                voice_name="▶ 继续第三章",
                description="进入第三章 (普通模式)",
                inner_voice="",
                next_node_id="ch2_resolution_normal",
                effects={"flag_set": ["chapter_complete_normal"]},
            ),
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_loss = ScriptedNode(
        node_id="ch2_resolution_loss",
        round_min=12,
        round_max=16,
        role="resolution",
        narrative=(
            "订单晚了半月，孙掌柜叹气：\n"
            "'沈老弟，这次...只能给八两。'\n"
            "\n"
            "你攥着银钱回家，张氏一句话也没说。"
            "父亲咳得更厉害了。\n"
            "\n"
            "——商誉受损，flag `merchant_disgraced`\n"
            "\n"
            "【第二章完 · 违约结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="continue_ch3_loss",
                voice_name="▶ 继续第三章 (困难模式)",
                description="声誉受损，进入第三章",
                inner_voice="",
                next_node_id="ch2_resolution_loss",
                effects={"flag_set": ["chapter_complete_loss"]},
            ),
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_outcast = ScriptedNode(
        node_id="ch2_resolution_outcast",
        round_min=12,
        round_max=16,
        role="resolution",
        narrative=(
            "又卖了织机，又卖了家具。\n"
            "\n"
            "你蹲在空荡荡的屋中，满脸木然。"
            "——梅雨、违约、赵师傅醉酒... 接踵而至。\n"
            "\n"
            "——flag `ch2_outcast`, `looms=0`\n"
            "\n"
            "【第二章完 · 破产结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    n_e_widow = ScriptedNode(
        node_id="ch2_resolution_widow",
        round_min=10,
        round_max=16,
        role="resolution",
        narrative=(
            "万历十五年八月初五，午时。\n"
            "\n"
            "张氏难产，母子俱亡。\n"
            "\n"
            "你抱着空襁褓，一夜白头。"
            "父亲：'儿啊，这命...'\n"
            "\n"
            "——flag `wife_dead`，孤身入第三章\n"
            "\n"
            "【第二章完 · 丧妻结局 · 隐藏结局】"
        ),
        voice_options=[
            ScriptedVoiceOption(
                voice_id="restart_ch2",
                voice_name="↺ 重玩",
                description="",
                inner_voice="",
                next_node_id="ch2_intro_normal",
                effects={"flag_set": ["restarted"]},
            ),
        ],
    )

    # ============================================================
    # 节点汇总
    # ============================================================
    nodes: dict[str, ScriptedNode] = {
        # 开局 (3 个变体)
        n1_prosperous.node_id: n1_prosperous,
        n1_normal.node_id: n1_normal,
        n1_father_secret.node_id: n1_father_secret,
        # escalation (5)
        n4_weave.node_id: n4_weave,
        n4_weave_late.node_id: n4_weave_late,
        n4_expand.node_id: n4_expand,
        n4_master.node_id: n4_master,
        n4_family.node_id: n4_family,
        # 🆕 v2.10.19: 深度支线 (6)
        n18_5_zhang_partner.node_id: n18_5_zhang_partner,
        n8_5_pregnant.node_id: n8_5_pregnant,
        n18_6_suzhou_compete.node_id: n18_6_suzhou_compete,
        n18_7_apprentice.node_id: n18_7_apprentice,
        # climax (10 + 2 新)
        n9_dye.node_id: n9_dye,
        n10_dye_success.node_id: n10_dye_success,
        n11_dye_fail.node_id: n11_dye_fail,
        n12_quality.node_id: n12_quality,
        n13_quality_partial.node_id: n13_quality_partial,
        n14_father_secret.node_id: n14_father_secret,
        n15_song.node_id: n15_song,
        n16_suzhou_news.node_id: n16_suzhou_news,
        n17_eunuch.node_id: n17_eunuch,
        n18_zhouqi.node_id: n18_zhouqi,
        n18_8_father_dying.node_id: n18_8_father_dying,
        n18_10_fire.node_id: n18_10_fire,
        n19_birth.node_id: n19_birth,
        n20_summary.node_id: n20_summary,
        # 结局 (5 + 2 新隐藏)
        n_e_prosperous.node_id: n_e_prosperous,
        n_e_normal.node_id: n_e_normal,
        n_e_loss.node_id: n_e_loss,
        n_e_outcast.node_id: n_e_outcast,
        n_e_widow.node_id: n_e_widow,
        n18_9_father_dead.node_id: n18_9_father_dead,
        n_e_fire.node_id: n_e_fire,
    }

    # ============================================================
    # 随机事件 (5 个)
    # ============================================================
    encounters: list[RandomEncounter] = [
        # 1. 梅雨连绵
        RandomEncounter(
            encounter_id="ch2_rainy_season",
            name="☔ 梅雨连绵",
            description="六月底梅雨，丝线潮湿易断",
            trigger_round_min=2,
            trigger_round_max=5,
            trigger_city="shengze",
            probability=0.4,
            check_attribute="luck",
            check_difficulty=10,
            great_success_sections=[
                _narrator("你抢晴天，拼命赶织。"),
                _npc("张氏", "相公，五匹绸出来了！", emotion="惊喜"),
            ],
            success_sections=[
                _narrator("梅雨虽长，你稳扎稳打。"),
            ],
            fail_sections=[
                _narrator("梅雨连绵三日，丝线断了三匹。"),
                _thought("订单怎么办？"),
            ],
            great_success_effects={"cash_delta": +2, "flag_set": ["rain_good"]},
            success_effects={"flag_set": ["rain_normal"]},
            fail_effects={"cash_delta": -1, "flag_set": ["silk_loss"]},
        ),
        # 2. 赵师傅求酒 (承 ch2_climax_dye)
        RandomEncounter(
            encounter_id="ch2_zhao_wine",
            name="🍶 赵师傅求酒",
            description="赵师傅欠酒债，央你帮忙",
            trigger_round_min=4,
            trigger_round_max=10,
            trigger_flags=["met_zhao"],
            trigger_city="shengze",
            probability=0.3,
            check_attribute="charisma",
            check_difficulty=12,
            great_success_sections=[
                _narrator("你请赵师傅喝了一顿酒。"),
                _npc("赵师傅", "沈老弟，你...是好人。这染色法，我教你。", emotion="感动"),
            ],
            success_sections=[
                _narrator("赵师傅点头：'罢了，我去戒酒。'"),
            ],
            fail_sections=[
                _narrator("赵师傅醉得更厉害了..."),
                _narrator("三匹绸颜色不均。"),
            ],
            great_success_effects={"flag_set": ["knew_color_master", "zhao_grateful"]},
            fail_effects={"cash_delta": -1, "flag_set": ["dye_failed"]},
        ),
        # 3. 苏州牙行抢单
        RandomEncounter(
            encounter_id="ch2_suzhou_offer",
            name="💰 苏州新订单",
            description="苏州牙行派人来盛泽抢单",
            trigger_round_min=5,
            trigger_round_max=11,
            trigger_city="shengze",
            probability=0.25,
            check_attribute="charisma",
            check_difficulty=11,
            great_success_sections=[
                _npc("苏州牙行", "沈老弟手艺了得，我出双倍！", emotion="欣赏"),
            ],
            success_sections=[
                _npc("苏州牙行", "沈老弟，加单 8 两。", emotion="平淡"),
            ],
            fail_sections=[
                _narrator("苏州牙行被别家抢走了..."),
            ],
            great_success_effects={"cash_delta": +15, "flag_set": ["new_suzhou_order"]},
            success_effects={"cash_delta": +8, "flag_set": ["added_order"]},
        ),
        # 4. 妻子难产 (承 wife_pregnant)
        RandomEncounter(
            encounter_id="ch2_wife_crisis",
            name="🤰 妻子难产",
            description="张氏临盆，胎位不正",
            trigger_round_min=7,
            trigger_round_max=13,
            trigger_flags=["wife_pregnant"],
            probability=0.6,
            check_attribute="cash",
            check_difficulty=10,
            great_success_sections=[
                _npc("王婆", "母子平安！沈家添丁！", emotion="喜"),
            ],
            success_sections=[
                _narrator("张氏咬牙撑过，但元气大伤。"),
            ],
            fail_sections=[
                _npc("王婆", "沈老弟，对不起...", emotion="哀"),
                _thought("这是命吗..."),
            ],
            great_success_effects={"cash_delta": -3, "flag_set": ["child_born", "call_doctor"]},
            fail_effects={"flag_set": ["wife_dead", "wife_crisis_failed"]},
        ),
        # 5. 织造太监采办 (前兆)
        RandomEncounter(
            encounter_id="ch2_eunuch_coming",
            name="🏛️ 太监采办前兆",
            description="苏州织造太监即将南下",
            trigger_round_min=7,
            trigger_round_max=12,
            probability=0.5,
            great_success_sections=[
                _narrator("周大娘悄悄告诉你：'沈老弟，李保的人要来盛泽了。'"),
            ],
            success_sections=[
                _narrator("镇上议论纷纷：'织造局的人要来了。'"),
            ],
            fail_sections=[
                _narrator("你错过了这个消息..."),
            ],
            great_success_effects={"flag_set": ["ch2_heard_eunuch", "early_warning"]},
            success_effects={"flag_set": ["ch2_heard_eunuch"]},
        ),
    ]

    chapter = ScriptedChapter(
        chapter_id=2,
        title="第二章：织染",
        subtitle="万历十五年六月至九月 · 盛泽镇 / 苏州府",
        description="苏州订单 · 家庭考验 · 织机扩张 · 染色危机",
        nodes=nodes,
        start_node_id="ch2_intro_normal",
        end_node_ids=[
            "ch2_resolution_prosperous",
            "ch2_resolution_normal",
            "ch2_resolution_loss",
            "ch2_resolution_outcast",
            "ch2_resolution_widow",
            "ch2_resolution_father_dead",
            "ch2_resolution_fire",
        ],
        total_rounds=16,
        estimated_play_minutes=15,
        theme="抉择 / 兴衰 / 家庭",
    )

    chapter.random_encounters = encounters  # type: ignore
    return chapter


_CHAPTER_CACHE = None


def get_chapter_02() -> ScriptedChapter:
    """获取第二章（缓存）"""
    global _CHAPTER_CACHE
    if _CHAPTER_CACHE is None:
        _CHAPTER_CACHE = build_chapter_02()
    return _CHAPTER_CACHE