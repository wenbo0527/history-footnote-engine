"""人设生成器（v1.3+）— DE 风格的「玩家塑造自己的声音」

根据玩家输入的"自由描述"和 era_config，生成：
- 基础档案（名字/家乡/家庭/口音/习惯）
- 3-5 个内在声音（DE 风格的"脑海中的声音"）
- 3-5 个初始技能（带等级）
- 1 段开场白草稿
- 初始 variables
"""
from __future__ import annotations

import json
from typing import Any


CHARACTER_GEN_PROMPT = """你是「历史注脚体验引擎」的人设生成器。

玩家想扮演的角色是：
{gender} · {identity_description}

期望生活/动机：{life_expectation}

时代背景：{era_name}（{era_year_range}）

## 你的任务
根据上述输入，生成一个**完整、可信、有人味儿**的人设档案。
玩家会**看到你的全部输出**，他/她可以选择微调或重新生成。

## 输出格式（严格 JSON）
```json
{{
  "name": "沈织户（或更真实的名字）",
  "hometown": "苏州府吴江县盛泽镇（或对应时代的地点）",
  "age": 30,
  "family": {{
    "spouse": "沈氏/张氏/...",
    "children": ["阿宝（8岁）", "小妹（4岁）"],
    "elderly": "老娘（60岁，住在邻村）"
  }},
  "background": "一两段话交代这个人的来历：为什么来到这个时代这个地方、家里有什么历史、本人有什么遗憾或执念",
  "personality": "三五个关键词描述这个人的性格",
  "tics": "一两个习惯性动作或口头禅（例：'搓手'、'说话时眼睛不看人'、'算账前先喝口茶'）",
  "starting_situation": "开局时这个人的具体处境：手头多少银子、家庭开支、即将面临的事件",

  "voices": [
    {{
      "id": "voice_xxx",
      "name": "内在声音的名字（要拟人、有画面感）",
      "trigger": "激活条件（变量阈值，如 'tax_burden>5'）",
      "description": "这个声音是什么——一个什么样的内在人格",
      "first_words": "它在特定场景下会主动说的第一句话"
    }}
  ],

  "skills": [
    {{
      "id": "skill_xxx",
      "name": "技能名（要符合时代，不带现代术语）",
      "level": 1-5,
      "description": "这个技能具体是什么"
    }}
  ],

  "opening_paragraph": "以这个人为主角的开场白，150-250字。半文半白、具体感官细节。不要泛泛说'你出生在...'"
}}
```

## 生成要求

1. **人设要可信**：不能是"完美英雄"或"彻底失败者"，要"在时代里挣扎但有自己坚持"
2. **时代要真实**：所有信息必须符合 {era_name} 的史实（不能用后世的语言/事物）
3. **声音要"对头"**：DE 的内在声音不是"小助手"，是"你脑海中那个总在提醒你的东西"——可以让人心烦、可以让人安心，但永远是你的一部分
4. **技能要"小人物"**：不是"战斗力/智力值"，而是"织布/算账/认字/种桑/说话周全"这种市井技能
5. **开局要有"具体的难处"**：手头紧/家里有事/外面有压力——让玩家第一回合就有"要做什么"的目标

## 万历十五年参考（可参考此类细节）
- 地点：苏州府吴江县盛泽镇（丝织重镇）
- 时代特征：万历不上朝、党争、倭寇、海禁、加派、矿税
- 物价：米一石约六钱银子、湖绫一匹六钱、束脩二两/年
- 口音/词汇：银子、织机、牙行、湖绫、桑叶、缫丝、梭子、经线、里长、里甲
"""


def build_character_prompt(era_config: dict, gender: str, identity_description: str, life_expectation: str, location: str = "", location_desc: str = "") -> str:
    """构造人设生成的 prompt"""
    era_name = era_config.get("era_name", "万历十五年")
    timeline = era_config.get("world", {}).get("timeline", {})
    start = timeline.get("start", {})
    end = timeline.get("end", {})
    era_year_range = f"{start.get('year', '?')}-{end.get('year', '?')}"

    # 注入 location 上下文
    location_block = ""
    if location or location_desc:
        location_block = "\n## 📍 玩家的位置（已锁定）\n"
        if location:
            location_block += f"**位置 ID**：{location}\n"
        if location_desc:
            location_block += f"**位置描述**：{location_desc}\n"
        location_block += (
            "\n> **关键约束**：玩家已选定了盛泽镇内的这个位置作为起点。\n"
            "> 你生成的人设必须**直接与这个位置绑定**——\n"
            "> 名字/家庭/背景/开局处境都要发生在这个具体地点。\n"
            "> **不要**把玩家放到其他镇/其他县/其他城。\n"
        )

    return CHARACTER_GEN_PROMPT.format(
        gender="男" if gender == "male" else "女",
        identity_description=identity_description or "（未指定，由你设计）",
        life_expectation=life_expectation or "（未指定，由你推测）",
        era_name=era_name,
        era_year_range=era_year_range,
    ) + location_block


def parse_character_response(content: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON"""
    import re
    # 尝试提取 ```json ... ``` 块
    m = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 直接尝试解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw": content}


# ============================================================
# 世界画卷生成（独立环节）
# ============================================================

WORLD_DWELL_PROMPT = """你是「历史注脚体验引擎」的世界画卷绘制师。

玩家即将进入的时代是：{era_name}（{era_year_range}）

时代包提供的关键信息：
{era_summary}

## 你的任务
写一段「世界画卷」——玩家在进入游戏前阅读的"时代背景铺垫"。

## 输出格式（严格 JSON）
```json
{{
  "title": "画卷标题（3-8字，要凝练）",
  "paragraphs": [
    "第一段：时代的远景（1-2句）",
    "第二段：地点的近景（嗅觉/听觉/视觉）",
    "第三段：关键人物/事件的影子（不直接说，留白）",
    "第四段：玩家作为一个小人物将面对的处境（1-2句）"
  ],
  "key_themes": ["这个时代将围绕的几个主题", "例：矿监/加税/倭寇/海禁"],
  "tone": "半文半白，沉静而不绝望"
}}
```

## 要求
1. **画卷要"立体"**——不是历史书，是"你站在这个时代里抬起头看到的景象"
2. **要有感官细节**——闻到/听到/看到的具体事物
3. **要留白**——不把时代说完，给玩家"进入后自己发现"的余地
4. **300-500字总长**——玩家要能 30 秒读完
"""


def build_world_dwell_prompt(era_config: dict) -> str:
    timeline = era_config.get("world", {}).get("timeline", {})
    start = timeline.get("start", {})
    end = timeline.get("end", {})
    era_year_range = f"{start.get('year', '?')}-{end.get('year', '?')}"

    # 提炼时代摘要
    era_summary_parts = []
    iron_laws = era_config.get("world", {}).get("iron_laws", [])
    if iron_laws:
        era_summary_parts.append("**历史红线**：")
        for law in iron_laws[:5]:
            era_summary_parts.append(f"- {law.get('fact', '')}")

    timeline_desc = timeline.get("description", "")
    if timeline_desc:
        era_summary_parts.append(f"\n**时代描述**：{timeline_desc}")

    return WORLD_DWELL_PROMPT.format(
        era_name=era_config.get("era_name", "万历十五年"),
        era_year_range=era_year_range,
        era_summary="\n".join(era_summary_parts),
    )


def parse_world_dwell(content: str) -> dict[str, Any]:
    """解析世界画卷 JSON"""
    import re
    m = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw": content}
