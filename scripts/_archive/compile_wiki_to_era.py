"""把两份Wiki编译到 era.json

输入：
  - 现有 era.json (25条entries)
  - Wiki v1.0 知识条目集 (16条)
  - Wiki v1.0 闲谈素材 (16条)

输出：
  - era.json (41条entries + 16条narrative_snippets)
"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")


# === Wiki v1.0 知识条目（16条）===
# 每条对应：id / layer / title / content / trigger_keywords / trigger_scene / related_entries / source_refs / confidence / needs_review

WIKI_ENTRIES = [
    # 01-时间骨架
    {
        "id": "bg_1587_key_dates",
        "layer": "background",
        "title": "1587年关键时间节点",
        "content": "1587年（万历十五年，丁亥，属猪），黄仁宇称'表面上四海升平，全年并无大事可叙'，但实际是帝国走向衰亡的契机。前序：1572万历即位、张居正辅政；1573-1582张居正新政（考成法、清丈田亩、一条鞭法试点）；1582张居正去世、改革势头衰减；1587皇帝开始消极怠政，朝政空转。后续：1589雒于仁上《四箴疏》直斥皇帝；1592-1598万历三大征（宁夏、朝鲜、播州）军费激增；1600前后矿税太监横行。1586-1588明经历第一次大天灾——黄河洪水接大旱，江南疫灾频度约36%。1587年（丁亥）无闰月，1588年（戊子）闰六月。",
        "trigger_keywords": ["万历十五年", "张居正", "三大征", "时间", "怠政", "丁亥"],
        "trigger_scene": [],
        "related_entries": ["bg_wanli_era", "pr_civil_military"],
        "source_refs": "黄仁宇《万历十五年》；明代江南疫灾地理研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "bg_lunar_calendar",
        "layer": "background",
        "title": "历法与节气",
        "content": "明代使用大统历，以阴历（太阴历）为基础，二十四节气按阳历太阳在黄道上的位置划分。朔望月约29.5天，12个月约354天，与阳历年差11天需置闰。对丝织户：节气决定农事节奏——清明前后桑树发芽→谷雨养蚕→小满蚕茧收获→芒种缫丝。市集日期与节气绑定，蚕丝市在立夏后最旺。赋税缴纳有固定期限与节气收成挂钩。",
        "trigger_keywords": ["节气", "阴历", "阳历", "二十四节气", "农事", "立夏", "清明", "谷雨", "小满", "芒种"],
        "trigger_scene": [],
        "related_entries": ["bg_1587_key_dates"],
        "source_refs": "吴军《答读者问14：二十四节气是怎么划分的呢？》",
        "confidence": "high",
        "needs_review": False,
    },
    # 02-空间舞台
    {
        "id": "sc_shengze_geo",
        "layer": "scene",
        "title": "盛泽镇地理",
        "content": "盛泽镇位于江苏省最南端，属苏州府吴江县，地处江苏、浙江、上海'两省一市'交汇的金三角地区。东、南与浙江嘉兴秀洲区王江泾镇接壤，西南与桃源镇相连，西与震泽镇交界，北与平望镇毗邻。地形为湖荡平原，全境无山，湖荡密布。北亚热带季风区，气候温和湿润。明弘治元年（1488）形成村落；明代中期，丝织家庭手工业以盛泽、黄家溪、新杭等地最为兴盛。享有'日出万绸，衣被天下'美称。万历年间尚未设镇建置（清顺治四年始设镇），但已是丝织业兴盛的市集聚落。",
        "trigger_keywords": ["盛泽", "地理", "位置", "江苏", "苏州", "湖荡", "吴江"],
        "trigger_scene": ["盛泽市集", "自家作坊"],
        "related_entries": ["sc_market_town", "sc_waterways"],
        "source_refs": "苏州地方志办'古镇古村系列——吴江区盛泽镇'",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_waterways",
        "layer": "scene",
        "title": "江南水路交通",
        "content": "江南交通以舟船为主，王士性记载万历中期江南'用舟船，无马'。盛泽周边水路：盛泽→平望镇半日（约15-20里）→吴江县城一日（约40里）→苏州府城一日半至两日（约80里，经平望、吴江）→嘉兴府一日（约50里，南下经王江泾）→震泽镇半日至一日（约30里）。出行：十里内步行、中长途航船（清晨出发傍晚到达，夜间不行船）、紧急雇快船。女性不单独远行需家人陪同。水路受天气影响——大风、暴雨、大雾均停航。",
        "trigger_keywords": ["水路", "船", "出行", "苏州", "嘉兴", "平望", "震泽", "王江泾"],
        "trigger_scene": ["盛泽市集", "镇外桑田"],
        "related_entries": ["sc_shengze_geo", "sc_jiangnan_six_prefectures"],
        "source_refs": "安徽省水利厅'水是江南经济发展的自然动力'；航运江南展览资料",
        "confidence": "medium",
        "needs_review": True,
    },
    {
        "id": "sc_jiangnan_six_prefectures",
        "layer": "scene",
        "title": "江南六府格局",
        "content": "狭义江南指苏州、松江、常州、杭州、嘉兴、湖州六府，环太湖流域，是明清最繁荣富庶之地。苏州府为行政中心，丝织品最大集散地，官营织染局所在地；嘉兴府盛泽南邻，蚕桑产区，王江泾为丝织重镇；湖州府蚕丝原料产地，丝价风向标；松江府棉布业中心，与丝绸互补；杭州府丝织品高端市场，文人消费中心。行政层级：盛泽→吴江县→苏州府→南直隶。",
        "trigger_keywords": ["苏州府", "杭州", "嘉兴", "湖州", "松江", "江南六府", "南直隶"],
        "trigger_scene": ["盛泽市集", "牙行"],
        "related_entries": ["sc_shengze_geo", "sc_waterways"],
        "source_refs": "中国通史第85集'江南市镇'",
        "confidence": "high",
        "needs_review": False,
    },
    # 03-社会结构
    {
        "id": "sc_shenming_ting",
        "layer": "scene",
        "title": "申明亭与三层调解",
        "content": "申明亭制度由洪武五年（1372）朱元璋始创。省、府、州、县、乡里都设申明亭，百姓违反国法的情况记载于榜上以示警告。里老人主持调解当地普通民事纠纷及轻微刑事案件。三层纠纷解决机制：第一层里老人调解（普通民事纠纷、不伤和气），第二层族老/乡绅（家族内部、宗祧继承、情理优先），第三层官府县衙（命案、重案、跨里甲纠纷、成本高耗时长）。实际运作：民众发生纠纷首先找'本都老人'，里老查看契约、实地勘查后调解，调解不成才上报县衙。官府批文有法律效力但执行依赖乡绅和宗族配合。对丝织户：丝价纠纷、织工工钱争议先找里老调解；行会内部纠纷行会首事先行处理；与外地客商的纠纷可能要到县衙诉讼；女性涉诉需男性亲属代为出面。",
        "trigger_keywords": ["申明亭", "调解", "里老", "纠纷", "县衙", "里甲"],
        "trigger_scene": ["县衙", "盛泽市集"],
        "related_entries": ["sc_zongzu", "en_li_jia"],
        "source_refs": "申明亭制度研究；徽州契约文书研究；明代宗祧继承纠纷研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_zongzu",
        "layer": "scene",
        "title": "宗族体系",
        "content": "江南宗族以祠堂为核心，族田为经济基础，族谱为血缘纽带。强房富族设有祭产专供祭祀之用。宗族功能：祭祀祖先（合族祭祖团拜，多在正月初一）、调解族内纠纷（族老主持优先于官府）、救济族内贫困（族田收入用于赈济）、教育族内子弟（义学、族塾）。对丝织户：小户丝织家庭可能依附大族获取保护；宗族网络是商业信用的重要基础；族内通婚巩固经济联盟；'上供'机会往往通过宗族关系获得。",
        "trigger_keywords": ["宗族", "祠堂", "族田", "族谱", "祭祖", "族老"],
        "trigger_scene": [],
        "related_entries": ["sc_shenming_ting"],
        "source_refs": "闽侯县民俗风情；徽州契约文书研究",
        "confidence": "medium",
        "needs_review": True,
    },
    {
        "id": "sc_women_status",
        "layer": "scene",
        "title": "女性法律地位",
        "content": "明代女性法律地位低下，不能独立诉讼、不能继承宗祧、不能拥有田产（寡妇例外可暂管）。但实际存在弹性空间。万历年间江南特殊情况：南京刑部档案显示，隆庆三年至万历十年间江南八府有37份由女性署名的验尸单与证词笔录；《明会典》载'遇案情紧要，可酌用谙晓事理之妇人协查闺闱、验伤问供'。女性在家庭经济中有实际影响力，尤其是丝织户家庭——妻子常参与缫丝、织造。沈氏（玩家妻子）的处境：可参与家庭丝织劳动、掌握缫丝技术；不能独立到市集交易，需丈夫或男性亲属在场；遇纠纷需男性亲属代为出面；但在家庭内部决策中有话语权，尤其是织造技术方面。",
        "trigger_keywords": ["女性", "沈氏", "寡妇", "诉讼", "验尸", "缫丝"],
        "trigger_scene": ["自家作坊", "盛泽市集"],
        "related_entries": ["sc_shenming_ting"],
        "source_refs": "《锦囊妙录》研究；南京刑部档案；《明会典》",
        "confidence": "medium",
        "needs_review": True,
    },
    {
        "id": "pr_late_ming_governance",
        "layer": "principle",
        "title": "晚明治理能力下降",
        "content": "专制集权软化：内阁职能增强，会议制度逐渐完善，大臣言谏风气张扬，党社活动活跃。但同时治理能力下降：政府权威衰落，政治分裂极端化，吏治腐败。社会控制松懈：明初里甲制编制监控网格加强对百姓管理，到万历年间里甲制已松弛，社会矛盾激化。对丝织户影响：官府执行力下降→商业纠纷解决变慢；矿税太监横行→额外盘剥；里甲制松弛→基层秩序依赖宗族和行会维持；党争→地方官员更替频繁，政策不稳定。",
        "trigger_keywords": ["晚明", "治理", "党争", "矿税", "内阁", "吏治"],
        "trigger_scene": [],
        "related_entries": ["bg_wanli_era", "en_kuang_jian", "en_li_jia"],
        "source_refs": "故宫学术讲坛'变与乱：正反两面看晚明'",
        "confidence": "high",
        "needs_review": False,
    },
    # 04-日常生活
    {
        "id": "pr_prices",
        "layer": "principle",
        "title": "万历物价体系与银钱兑换",
        "content": "货币：1两=10钱=100分=1000厘；白银形态有大元宝50两/锭、小元宝5两/锭、日常碎银（剪凿称重）；铜钱1两银≈700-1000文（万历年间波动大，金背钱约400文换1两）；纸钞（大明宝钞）已基本废用。1分银购买力：果蔬约1斤多、葱姜约5斤（0.2分/斤）、酒约1斤、肉/鱼约0.5斤（标准价2分/斤）。1钱银（10分）：米约2-3斗、肉约5斤、鸡约1-2只、中等布匹约1尺、雇工约3-5天工钱。1两银：米约2石（1石≈94.4公斤）、猪约1头、雇工约1个月工钱、普通衣裳约1件、书约1册。万历1两银≈540-750元人民币（米价折算）。丝织品：绫0.8-1.2两/匹、罗0.6-0.9两/匹、绸0.4-0.7两/匹、缎1.0-1.5两/匹、绢0.3-0.5两/匹。",
        "trigger_keywords": ["物价", "一两", "一钱", "银", "米价", "铜钱", "工钱", "折合"],
        "trigger_scene": ["牙行", "盛泽市集"],
        "related_entries": ["sc_diet", "sc_clothing", "bg_silver_age"],
        "source_refs": "卜正民《崩盘》；第一财经节选；《烟花春梦》；《金瓶梅》物价研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_diet",
        "layer": "scene",
        "title": "饮食与社会层级",
        "content": "雇工食物消费（王家范据沈氏《农书》整理）：长工一年口粮每日一升五合（偏高标准）。一般江南农家'二稀一乾'即为佳境——早晚稀饭中午干饭；困苦时两稀度日，农忙才吃干饭。饮食结构：雇工/贫户以二稀一乾蔬菜为主少肉、过年有肉；小户丝织家庭稀饭+蔬菜+偶尔鱼虾、节庆有荤菜；机户/作坊主干饭为主常有鱼虾肉、宴客有酒有肉；富商/乡绅精米白面荤素搭配、山珍海味。江南特色：主食大米（粳米）、蔬菜青菜萝卜黄瓜菱芡藕、荤菜猪肉（2分/斤）鱼虾鸡鸭、调味葱姜酱醋、酒米酒（1分/斤到20分/瓶）。丝织户特殊：缫丝季（谷雨至小满）劳动强度大需加餐（干饭+咸鱼/咸肉）；织造时久坐常饮茶提神；市集日可能在茶馆/食摊用餐。",
        "trigger_keywords": ["饮食", "雇工", "沈氏", "二稀一干", "缫丝", "农书", "米酒"],
        "trigger_scene": ["自家作坊", "盛泽市集", "茶馆"],
        "related_entries": ["pr_prices"],
        "source_refs": "王家范《明清江南消费风气与消费结构描述》；卜正民《崩盘》",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_clothing",
        "layer": "scene",
        "title": "服饰与等级",
        "content": "晚明江南形成'时尚'之风，'唱自一人'而'群起而随之'，形成区域性甚至全国性冲击波。'时样'：浅面矮跟鞋、笔管水袜等。服饰按层级：雇工/贫户穿粗布短衣草鞋（棉布麻布），小户丝织家庭穿自织绢布衣裳（绢棉布），机户/作坊主穿绸缎衣裳（绸绫），富商/乡绅穿精致绸缎（缎罗绫）。价格（《金瓶梅》物价）：普通衣裳约1两/件、绸缎衣裳约12两/套、貂鼠皮袄60两（奢侈品）。丝织户特殊：自家织造，穿着比同等收入家庭体面，但好料子要卖钱，自穿多用次等品或余料。",
        "trigger_keywords": ["服饰", "时样", "绸缎", "衣裳", "皮袄", "矮跟"],
        "trigger_scene": ["自家作坊", "盛泽市集"],
        "related_entries": ["pr_prices"],
        "source_refs": "《风物闲美：晚明江南生活》；《金瓶梅》物价研究；明代中后期江南庶民服饰研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_housing",
        "layer": "scene",
        "title": "江南住房格局",
        "content": "江南民居临水而建，前街后河，砖木结构白墙灰瓦，一般两进（前进客厅+后进卧室），楼上储物/织造楼下起居。丝织户住房：织机占空间大（一台织机约需2×3米），住房需专门辟出织造间；缫丝需靠近水源（热水缫丝），厨房与缫丝间常相邻；染丝需通风晾晒，院落或天井不可少；小户可能只有一间半房（半间织造+一间起居）。住房成本暂缺具体数据，参考《金瓶梅》夏提刑住宅1200两，普通民房估计在5-20两之间。",
        "trigger_keywords": ["住房", "临水", "织机", "缫丝", "院落", "白墙"],
        "trigger_scene": ["自家作坊"],
        "related_entries": ["pr_prices", "sc_silk_workshop"],
        "source_refs": "综合推断",
        "confidence": "low",
        "needs_review": True,
    },
    {
        "id": "sc_festivals",
        "layer": "scene",
        "title": "节庆与年历",
        "content": "主要节庆：元旦（正月初一，祭祖团拜走亲，年终结算收欠款）；元宵（正月十五赏灯猜谜，丝绸灯面需求）；清明（三月扫墓踏青，桑树发芽养蚕准备）；立夏（四月进新麦，蚕茧将熟缫丝准备）；端午（五月初五赛龙舟吃粽子，丝市旺季开始）；七夕（七月初七乞巧，织女崇拜织工节日）；中元（七月十五祭祖城隍出巡，厉坛祭典）；中秋（八月十五赏月吃月饼，秋丝上市）；重阳（九九登高，秋季丝市尾声）；冬至（十一月祭祖，年终账目清理）；腊八（十二月初八吃腊八粥准备年货）。城隍三巡会：清明、中元、下元城隍神像出巡至厉坛，'必极巡游之盛'，'致一国若狂'，市集拥挤热闹。",
        "trigger_keywords": ["节庆", "七夕", "城隍", "元宵", "端午", "中秋", "清明", "冬至", "三巡会"],
        "trigger_scene": ["盛泽市集", "茶馆"],
        "related_entries": ["sc_folk_belief", "bg_lunar_calendar"],
        "source_refs": "城隍信仰研究；江南民俗综合",
        "confidence": "medium",
        "needs_review": True,
    },
    # 05-时代张力
    {
        "id": "pr_land_conflict",
        "layer": "principle",
        "title": "人地矛盾与种植业转型",
        "content": "核心矛盾：江南'苏湖熟，天下足'→人口增多→耕地变少→人地矛盾凸显→被迫转向经济作物。转型路径：耕地少→蚕桑地增多→粮食依赖湖广地区→'人多地少，赋税重，逼迫种植业转型，转向经济型'。对丝织户影响：桑田挤占粮田→本地米价受外部影响大；丝织业回报高于种粮→更多农户转向丝织；但丝织完全依赖市场→丝价波动直接影响生计；粮食不能自给→一旦外地粮运受阻立即面临饥荒风险。",
        "trigger_keywords": ["人地矛盾", "桑田", "粮田", "湖广", "苏湖熟", "种植业"],
        "trigger_scene": ["镇外桑田"],
        "related_entries": ["bg_north_south", "pr_silver_inflow"],
        "source_refs": "中国通史第85集'江南市镇'",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "pr_silver_inflow",
        "layer": "principle",
        "title": "白银内流与物价变动",
        "content": "隆庆开关：1567年明廷解除海禁，月港成为唯一合法民间贸易港。中国深度参与全球贸易网络，通过丝绸、瓷器换回大量白银。白银对物价的影响：白银内流→银价购买力缓慢下降；万历年间1两银≈540元（嘉靖九年约745元）；但正常年景物价相对稳定，灾荒年景米价可暴涨数倍。卜正民发现：明朝前两百年物价出奇稳定，最后的粮价飙升完全由小冰期驱动。对丝织户影响：丝绸出口需求旺盛→丝价有支撑；但白银贬值→实际收入可能缩水；赋税折银→银贵时吃亏银贱时略好；灾荒年景米价暴涨但丝价不一定跟涨→'有丝无粮'的困境。",
        "trigger_keywords": ["白银", "隆庆开关", "银价", "折银", "月港", "小冰期", "海禁"],
        "trigger_scene": ["牙行", "盛泽市集"],
        "related_entries": ["bg_silver_age", "pr_land_conflict", "en_yitiao_bian"],
        "source_refs": "卜正民《崩盘》；隆庆开关研究",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_consumption",
        "layer": "scene",
        "title": "消费风气与贫富差距",
        "content": "明中叶后江南消费风气趋向奢靡。苏州府'唯马首是瞻'影响全国。松江府'吾松素称奢侈，今黠傲之俗，已无还淳挽朴之机'。消费结构畸形：上层饮食肴馔、园林建筑、古董艺玩、服饰竞奢；底层食物消费占收入绝大部分几乎没有余力消费其他。雇工年食物消费约5两银，而最低日工资仅2-3分银。对丝织户影响：奢靡风气→高端丝织品需求旺盛→做高端有利润；但底层消费力弱→中低端丝织品市场有限；'做大做强准备上供'→进入官府采购体系是关键跃升；消费风气变化快→'时样'更替→库存风险。",
        "trigger_keywords": ["奢靡", "消费", "时尚", "时样", "上供", "马首是瞻"],
        "trigger_scene": ["牙行", "盛泽市集"],
        "related_entries": ["pr_tribute_economy", "pr_silver_inflow"],
        "source_refs": "王家范《明清江南消费风气历史探测'",
        "confidence": "high",
        "needs_review": False,
    },
    # 06-认知地图
    {
        "id": "pr_vocabulary",
        "layer": "principle",
        "title": "丝织户话语体系",
        "content": "命运观词汇：命（先天注定的人生轨迹，'命里该当''命不好'），运（后天变化的际遇，'时运''运气''走运'），天意（超越人力的意志，旱灾瘟疫时感叹），造化（际遇运气偏正面，'造化弄人''好造化'），报应（善恶因果，警告解释灾祸），时运（当下的运气，'时运不济''时来运转'），命数（寿命定数，生死关头）。江南吴语中的运气表达：'额角头高'（运气好）、'触霉头'（倒霉）、'额角头碰着天花板'（最幸运）、'老虫跌勒米缸里'（谋到好工作）、'瞎猫碰着死老虫'（误打误撞成功）、'痴人有痴福'（傻人有傻福）、'拾着皮夹子'（意外之财）。赋税相关用语：'上供'（向官府供应丝织品）、'加派'（额外征收）、'折银'（实物税折算白银）、'一条鞭法'（赋役合并折银征收）。丝织行话：'经'（经线）、'纬'（纬线）、'提花'（织造花纹）、'缫丝'（从蚕茧抽丝）、'练丝'（脱胶处理）、'染坊'（染色作坊）、'牙人'（中间商）、'行面'（行会评估的丝织品等级）。",
        "trigger_keywords": ["行话", "命运", "运气", "时运", "造化", "额角头", "触霉头", "经", "纬", "提花"],
        "trigger_scene": ["茶馆", "盛泽市集", "自家作坊"],
        "related_entries": ["sc_proverbs", "sc_folk_belief"],
        "source_refs": "无锡地方俗语；陈江'明代江南俗语所见之社会情态'；综合推断",
        "confidence": "medium",
        "needs_review": True,
    },
    {
        "id": "sc_proverbs",
        "layer": "scene",
        "title": "江南俗语与社会情态",
        "content": "人际关系变化（陈江研究）：明代中后期江南传统三纲五常受到空前冲击。南京地区流行的俗语反映的行为——'趋''卤''淡''拿''捏''熏''冷''吊''灸''撩'——已全然看不出仁义礼智信。顾起元诠释：'趋'/'呵'（阿承显富），'卤'（以言诳人而沁入之），'淡'（示若不置人于意中），'拿'/'捏'（持人之阴事使不敢肆），'齅'（风而使其从我），'熏'（以语渐渍之俾其从）。价值观念变化：传统'重义轻利'→'义利并重'甚至'重利轻义'；'有柴有米是夫妻，无柴无米各东西'——物质基础决定关系；'金乡邻，银亲眷'——邻里关系比亲戚更实际。对丝织户的意义：商业社会人际关系更功利化；'趋'富避贫是常态——做大做强才有话语权；'拿''捏'——知道别人的秘密是权力来源；传统道德约束力下降→契约和行规更重要。",
        "trigger_keywords": ["俗语", "趋", "卤", "拿", "捏", "重义轻利", "金乡邻"],
        "trigger_scene": ["茶馆", "盛泽市集"],
        "related_entries": ["pr_vocabulary", "bg_moral_system"],
        "source_refs": "陈江'明代江南俗语所见之社会情态'",
        "confidence": "high",
        "needs_review": False,
    },
    {
        "id": "sc_folk_belief",
        "layer": "scene",
        "title": "民间信仰与禁忌",
        "content": "万历年间江南民间信仰体系：城隍信仰（清明、中元、下元三巡会，护城佑民赏善罚恶）；祖先崇拜（元旦、清明、中元、冬至、忌日，家族凝聚祈求庇佑）；行业神（织女/嫘祖，七夕，丝织业保护神）；自然神（土地、龙王，旱涝时祈雨祈晴）；风水（建房修坟选址择吉）；占卜（日常决策卜吉凶）。《留青日札》记载：田艺蘅（嘉靖至万历年间浙江钱塘人）撰有《留青日札》，'凡经史子集、典章制度、音韵训诂、社会风尚、民生疾苦、艺林传闻、掌故逸事等，无所不涉'，记录了万历年间江南民间信仰实态。丝织户的信仰实践：七夕乞巧——织工最重要的节日，祈求织技精进；开工前祭织女——新织机启用、新花色开织；蚕神信仰——养蚕前祭蚕神，祈求蚕茧丰收；城隍庙——纠纷调解、许愿还愿；祖先牌位——厅堂设龛，日常上香。禁忌：缫丝时不能说'断'（怕丝断）；织造时不能说'破'（怕布破）；养蚕时不能大声喧哗（怕惊蚕）；卖丝不能在城隍庙前（怕神明看见争利）。",
        "trigger_keywords": ["城隍", "织女", "蚕神", "禁忌", "风水", "占卜", "留青日札", "嫘祖"],
        "trigger_scene": ["盛泽市集", "自家作坊", "茶馆"],
        "related_entries": ["pr_vocabulary", "sc_festivals"],
        "source_refs": "《留青日札》研究；城隍信仰研究；江南民俗综合",
        "confidence": "medium",
        "needs_review": True,
    },
    {
        "id": "pr_knowledge_boundary",
        "layer": "principle",
        "title": "丝织户的知识边界",
        "content": "丝织户知道什么/不知道什么：本地——知道丝价米价行会规矩本地官吏邻里关系，不知道县衙内部运作细节；行业——知道织造技术品种行情客商偏好染料来源，不知道全国丝绸总产量出口量；天下——知道万历皇帝在位张居正已死辽东有战事，不知道朝廷决策过程具体战况财政数据；自然——知道节气与农事天气征兆蚕病识别，不知道气候变化原因疫病机理；信仰——知道城隍织女祖先风水，不知道佛道经典神学体系。信息来源：市集上的口口相传、行会内部消息、茶馆里的闲谈、官府告示、走商带来的外地消息。信息传播速度：盛泽本地当天、吴江县内1-2天、苏州府内3-5天、外省消息1-3个月、朝廷消息视距离和重要性1-6个月。",
        "trigger_keywords": ["知道", "不知道", "信息", "传闻", "走商", "市集", "茶馆", "告示"],
        "trigger_scene": ["茶馆", "盛泽市集"],
        "related_entries": ["bg_wanli_era", "pr_vocabulary"],
        "source_refs": "综合推断",
        "confidence": "low",
        "needs_review": True,
    },
]


# === Wiki v1.0 闲谈素材（16条）===
# 每条对应：id / source / applies_to_scenes / snippet_text / npc_use_case / trigger_keywords

NARRATIVE_SNIPPETS = [
    {
        "id": "sn_shishi_shifu_market",
        "source": "《醒世恒言》第十八卷'施润泽滩阙遇友'",
        "applies_to_scenes": ["盛泽市集", "牙行", "自家作坊"],
        "trigger_keywords": ["盛泽", "市集", "牙行", "绸丝", "热闹"],
        "npc_use_case": "DM描写市集热闹时引用，或让NPC感叹'这盛泽镇啊'",
        "snippet_text": "镇上居民稠广，土俗淳朴，俱以蚕桑为生。男女勤谨，络纬机杼之声，通宵彻夜。那岸上两岸绸丝牙行，约有千百余家，远近村坊织成绸匹，俱到此上市。四方商贾来收买的，蜂攒蚁集，挨挤不开，路途无伫足之隙，乃出产锦锈之乡，积聚绫罗之地。",
    },
    {
        "id": "sn_shishi_capital",
        "source": "《醒世恒言》第十八卷",
        "applies_to_scenes": ["自家作坊", "牙行"],
        "trigger_keywords": ["织机", "添置", "扩大", "本钱", "利息"],
        "npc_use_case": "老织工传授经验——'你看施家，当年就是从一张机起家'",
        "snippet_text": "今日好造化！拾得这些银子，正好将去凑做本钱。有了这银子，再添上一张机，一月出得多少绸，有许多利息。积上一年，共该若干，到来年再添上一张，一年又有多少利息。算到十年之外，便有千金之富。",
    },
    {
        "id": "sn_shishi_sell",
        "source": "《醒世恒言》第十八卷",
        "applies_to_scenes": ["牙行", "盛泽市集"],
        "trigger_keywords": ["卖绸", "牙行", "客商", "成色"],
        "npc_use_case": "DM描述卖绸场景，牙行交易流程",
        "snippet_text": "施复来到市上，只听人语喧嚷，十分热闹。他也不管这些，直接到熟悉的绸布店去。只见门口拥着好多卖绸的，屋里坐着三四个客商。店主人站在柜台里，把那些绸子一匹匹展开，看成色，叫喊着价钱。",
    },
    {
        "id": "sn_shishi_silver",
        "source": "《醒世恒言》第十八卷",
        "applies_to_scenes": ["茶馆", "盛泽市集"],
        "trigger_keywords": ["拾金", "还银", "道德", "施家"],
        "npc_use_case": "NPC讲'施家还银'的故事作为道德参照",
        "snippet_text": "这钱如果是富人丢的，就像牛身上掉了一根毛，没什么损失；如果是客商的，这是他离妻别子、风餐露宿，辛勤挣来的钱，丢了一定非常难过。有本钱的还能承受这种损失，倘然做的是小生意……",
    },
    {
        "id": "sn_shishi_treasure",
        "source": "《醒世恒言》第十八卷",
        "applies_to_scenes": ["自家作坊", "盛泽市集", "茶馆"],
        "trigger_keywords": ["买房", "挖", "藏银", "旧宅"],
        "npc_use_case": "邻居闲聊——'听说施家买那旧宅子，翻地时挖出一坛银子来'",
        "snippet_text": "施复买邻家旧房，挖掘时竟得千金藏银。后又盖房再得千金。小说归因为还银善报，但实际反映的是明代江南房产交易中'地下藏银'的普遍现象。",
    },
    {
        "id": "sn_shishi_chicken",
        "source": "《醒世恒言》第十八卷",
        "applies_to_scenes": ["镇外桑田"],
        "trigger_keywords": ["借宿", "农家", "鸡", "禁忌"],
        "npc_use_case": "NPC讲古——'鸡是有灵性的，施家那回要不是鸡叫，人早没了'",
        "snippet_text": "施复在朱恩家借宿，朱恩要杀鸡款待，施复劝阻。当夜鸡群乱叫，施复起身查看，刚离开床铺，一根车轴砸在铺上——若非鸡叫，必死无疑。",
    },
    {
        "id": "sn_jpm_gift",
        "source": "《金瓶梅词话》",
        "applies_to_scenes": ["茶馆", "盛泽市集"],
        "trigger_keywords": ["上供", "送礼", "寿礼", "官府"],
        "npc_use_case": "NPC感叹——'你知道上供要送什么吗？'",
        "snippet_text": "西门庆送给蔡太师的寿礼包括：两副玉桃杯，两套杭州织造的大红五彩罗缎丝蟒衣，至少两匹玄色焦布和大红纱蟒。",
    },
    {
        "id": "sn_jpm_wage",
        "source": "《金瓶梅词话》",
        "applies_to_scenes": ["牙行", "盛泽市集", "自家作坊"],
        "trigger_keywords": ["工钱", "雇工", "丫头", "伙计"],
        "npc_use_case": "牙人报价——'一个丫头五六两，你那织工一个月工钱也得一两起步吧'",
        "snippet_text": "一个10岁左右的普通丫头身价约五两至六两银子；生药铺伙计傅铭每月工钱二两银子；温秀才每月三两；乐工李铭每月五两。",
    },
    {
        "id": "sn_jpm_clothes",
        "source": "《金瓶梅词话》",
        "applies_to_scenes": ["盛泽市集", "自家作坊"],
        "trigger_keywords": ["衣裳", "绸缎", "皮袄", "服饰"],
        "npc_use_case": "妻子沈氏感叹——'你看城里那些太太，一件衣裳就十二两'",
        "snippet_text": "常时节为妻子买5件衣裳、自己2件，共六两五钱银子，每件约一两。西门庆为李桂姐置四套绸缎衣裳需五十两，每套约十二两。李瓶儿一件貂鼠皮袄需六十两。",
    },
    {
        "id": "sn_jpm_official",
        "source": "《金瓶梅词话》",
        "applies_to_scenes": ["茶馆", "县衙"],
        "trigger_keywords": ["官场", "上供", "鼎", "识趣"],
        "npc_use_case": "老机户传授——'当官的看上你什么，你可得识趣'",
        "snippet_text": "宋御史多看了几眼西门庆家的镏金鼎，西门庆心领神会，立刻派人送去。宋御史假意推辞：'学生还当奉价。'西门庆道：'早知我正要奉送公祖，犹恐见却，岂敢云价。'",
    },
    {
        "id": "sn_sanyan_pearl",
        "source": "《喻世明言》第一卷'蒋兴哥重会珍珠衫'",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["远行", "做买卖", "夫妻", "珍珠衫"],
        "npc_use_case": "茶馆闲谈——'你听说了吗？蒋家那事'",
        "snippet_text": "蒋兴哥是湖广襄阳商人，世代到广东做买卖。妻子在家独守，因一件珍珠衫与客商陈商发生感情。后蒋兴哥发现真相，并未声张，而是以'休书'方式体面分手。最终二人在异地重逢，破镜重圆。",
    },
    {
        "id": "sn_sanyan_orange",
        "source": "《初刻拍案惊奇》第一卷'转运汉巧遇洞庭红'",
        "applies_to_scenes": ["茶馆", "盛泽市集"],
        "trigger_keywords": ["运气", "海外", "意外", "赚钱"],
        "npc_use_case": "织工闲聊——'运气来了挡都挡不住'",
        "snippet_text": "文若虚本是落魄文人，随商船出海，以一两银子买了洞庭红橘子。到了海外，橘子被抢购一空，赚了大钱。后又在一具龟壳中发现珍珠，暴富。",
    },
    {
        "id": "sn_sanyan_oil",
        "source": "《醒世恒言》第三卷'卖油郎独占花魁'",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["小人物", "逆袭", "攒钱", "真情"],
        "npc_use_case": "市井闲谈——'你看那卖油的秦重'",
        "snippet_text": "卖油小贩秦重，省吃俭用攒了一年银子，只为见花魁娘子一面。最终以真情打动花魁，成就姻缘。",
    },
    {
        "id": "sn_shen_wansan",
        "source": "中国通史第85集+民间传说",
        "applies_to_scenes": ["茶馆"],
        "trigger_keywords": ["做大", "富商", "沈万三", "风险"],
        "npc_use_case": "老织工警告——'做大了也不是好事'",
        "snippet_text": "明初，周庄商人沈万三富可敌国，捐资帮助朱元璋修筑南京城墙。朱元璋怒曰：'匹夫犒天子军，乱民也！'最终在马皇后劝解下，沈万三被发配云南，洪武二十六年卷入蓝玉党案，从此萧条没落。",
    },
    {
        "id": "sn_canshen_temple",
        "source": "盛泽先蚕祠实地记载",
        "applies_to_scenes": ["盛泽市集"],
        "trigger_keywords": ["小满", "蚕神", "先蚕祠", "庙会"],
        "npc_use_case": "DM描述小满节庆——'先蚕祠前人山人海'",
        "snippet_text": "盛泽先蚕祠供奉嫘祖、轩辕、神农三位先祖。嫘祖被尊为'蚕花娘娘''蚕神''先蚕'。小满那天是蚕神生日，先蚕祠人头攒动，锣鼓喧天，古戏台上好戏连演三天。蚕农饮水思源，以恭敬诚恳的心情感谢神灵庆贺丰收。",
    },
    {
        "id": "sn_suzhou_tax",
        "source": "综合史料",
        "applies_to_scenes": ["茶馆", "县衙"],
        "trigger_keywords": ["苏州", "税负", "重税", "赋税"],
        "npc_use_case": "里老叹气——'咱苏州府的税，全国最重'",
        "snippet_text": "朱元璋对苏州实施严厉惩罚——将苏州居民大量强制迁徙到江北，还制定全国最重的税负标准。苏州府田地只占全国百分之一左右，却要负担全国近十分之一的田亩税。此外还要为皇宫提供大量丝绸锦缎，基本属于半买半上贡。",
    },
]


def main():
    config = json.loads(ERA_PATH.read_text(encoding="utf-8"))

    # 1. 追加知识条目
    existing_ids = {e["id"] for e in config["knowledge"]["entries"]}
    added_entries = 0
    for entry in WIKI_ENTRIES:
        if entry["id"] not in existing_ids:
            config["knowledge"]["entries"].append(entry)
            added_entries += 1

    # 2. 新增 narrative_snippets 字段
    if "narrative_snippets" not in config["knowledge"]:
        config["knowledge"]["narrative_snippets"] = []
    existing_snip_ids = {s["id"] for s in config["knowledge"]["narrative_snippets"]}
    added_snippets = 0
    for snip in NARRATIVE_SNIPPETS:
        if snip["id"] not in existing_snip_ids:
            config["knowledge"]["narrative_snippets"].append(snip)
            added_snippets += 1

    # 3. 写回
    ERA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 添加知识条目 {added_entries} 条")
    print(f"✅ 添加闲谈片段 {added_snippets} 条")
    print(f"📊 当前 totals: entries={len(config['knowledge']['entries'])}, snippets={len(config['knowledge']['narrative_snippets'])}")


if __name__ == "__main__":
    main()
