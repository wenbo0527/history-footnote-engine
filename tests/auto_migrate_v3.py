"""🆕 v2.10.30 — 自动批量迁移 v3 (stateful + emotion inference)

相比 v2 改进:
- Stateful: 跟踪 current NPC, 后续引号台词归属正确
- Emotion: 从 (忧)/(喜)/(惊恐)/(假笑) 等括号注解推断
- NPC quotes: 单引号/双引号开头的台词归属当前 NPC
- 嵌套引号: 处理转义引号
"""
import re
import sys
from pathlib import Path

CHAPTERS = {
    1: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_01.py',
    2: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_02.py',
    3: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_03.py',
}

KNOWN_NPCS = {
    "张氏", "父亲", "父亲沈茂", "钱老板", "钱少", "周大娘", "张叔", "赵师傅",
    "孙掌柜", "掌柜", "王掌柜", "王婆", "陈小", "陈师傅", "李保", "太监", "太监李保",
    "周七", "刘二", "宋明", "王公", "母亲", "牙行掌柜", "白头翁", "税关",
    "苏州恒德祥", "内衙",
}

EMOTION_KEYWORDS = {
    # 中文 emotion 关键词
    "忧", "喜", "怒", "哀", "恐", "惊", "平静",
    "假笑", "苦笑", "冷笑", "强笑",
    "点头", "摇头", "叹气", "皱眉", "瞪眼", "苦笑", "假笑", "低头", "抬头",
    "郑重", "正色", "严肃", "神秘", "阴沉", "试探", "激昂", "惊叹",
    "气弱", "气喘", "惊恐", "气喘吁吁", "涨红了脸", "面有喜色", "满脸通红",
    "为难", "羞", "惊", "嘿嘿",
}


def extract_emotion(text: str) -> tuple[str, str]:
    """从 text 提取 (clean_text, emotion)

    例如: '相公，门外有客。' -> ('相公，门外有客。', '')
    例如: '相公（忧）：门外有客' -> ('相公：门外有客', '忧')
    """
    # 模式 1: 文本后接 (emotion)
    m = re.search(r"\s*[（(]([^（）()]+)[）)]\s*$", text)
    if m:
        emotion = m.group(1)
        # 仅当 emotion 是已知情绪
        if any(k in emotion for k in EMOTION_KEYWORDS) or len(emotion) <= 4:
            text = re.sub(r"\s*[（(]([^（）()]+)[）)]\s*$", "", text).strip()
            return text, emotion
    return text, ""


def classify_line_st(line: str, current_npc: list[str], prev_narrator: list[str] = None) -> tuple[str, dict, list[str]]:
    """启发式分类一行 (stateful)

    Args:
        line: 单行文本
        current_npc: 当前 NPC 上下文 (mutable, 单元素列表)
        prev_narrator: 前一行 narrator (用于推测 NPC)

    Returns:
        (sec_type, kwargs, new_current_npc)
    """
    if prev_narrator is None:
        prev_narrator = [""]
    line = line.strip()
    if not line:
        return ("skip", {}, current_npc)

    # 1. 「...」开头 → thought
    if line.startswith("「"):
        inner = line.lstrip("「").rstrip("」").rstrip("。")
        return ("thought", {"text": inner}, current_npc)

    # 2. 'XX道：' / 'XX说：' 等动词 → npc (更新 current_npc)
    m = re.match(
        r"^([\u4e00-\u9fa5·]{1,8})(道|说|叹|应|答|笑|问|喊|低声道|笑着说|低声|回答|轻声说)[:：]\s*(.+)",
        line,
    )
    if m:
        text, emotion = extract_emotion(m.group(3))
        return ("npc", {"name": m.group(1), "text": text, "emotion": emotion}, [m.group(1)])

    # 3. 'XX：' 开头 → npc (更新 current_npc)
    m = re.match(r"^([\u4e00-\u9fa5·]{1,8})[:：]\s*(.+)$", line)
    if m:
        name = m.group(1)
        if name in KNOWN_NPCS or (1 <= len(name) <= 4 and "·" not in line):
            text = m.group(2)
            # 处理 "'我教你一招' 这种带引号的台词"
            if text.startswith("'") and text.endswith("'") or text.startswith('"') and text.endswith('"'):
                text = text.strip("'\"")
            text, emotion = extract_emotion(text)
            return ("npc", {"name": name, "text": text, "emotion": emotion}, [name])

    # 3.5 推测 NPC: 行末尾是 `：/:` (即将有台词)
    # 例: "她让你坐下，神秘兮兮：" → 推测下个 NPC 是 "她"
    #     "周大娘神秘地说：" → 推测下个 NPC 是 "周大娘"
    # 但通常这种句子本身是 narrator, 需要更智能
    if line.endswith("：") or line.endswith(":"):
        # 寻找句中可能 NPC 名 (1-4 字中文, 按 NPC 名长度降序优先匹配)
        npcs_in_line = re.findall(r"([\u4e00-\u9fa5·]{1,4})", line)
        # 按 NPC 长度降序 (优先匹配长 NPC 名)
        sorted_npcs = sorted(KNOWN_NPCS, key=len, reverse=True)
        for word in npcs_in_line:
            for npc in sorted_npcs:
                if npc in word:
                    current_npc[0] = npc
                    break
            if current_npc[0] != "旁白":
                break
        # 也看上一行 narrator
        if current_npc[0] == "旁白" and prev_narrator[0]:
            npcs_in_prev = re.findall(r"([\u4e00-\u9fa5·]{1,4})", prev_narrator[0])
            for word in npcs_in_prev:
                for npc in sorted_npcs:
                    if npc in word:
                        current_npc[0] = npc
                        break
                if current_npc[0] != "旁白":
                    break

    # 4. 【XXX】前缀 → npc
    m = re.match(r"^【([\u4e00-\u9fa5·]{1,8})】\s*(.+)", line)
    if m:
        text, emotion = extract_emotion(m.group(2))
        return ("npc", {"name": m.group(1), "text": text, "emotion": emotion}, [m.group(1)])

    # 5. 含拟声词 → sound
    soundeffects = ["咚", "咳", "嘶", "哗", "嗡", "鸣", "沙沙", "呼呼", "噼啪", "吱呀", "扑通", "咕嘟", "砰砰", "叮", "唰", "呜", "啪", "踢踏", "咯咯", "唰唰", "唢呐"]
    for se in soundeffects:
        if se in line:
            return ("sound", {"sound": line}, current_npc)

    # 6. '——flag' → thought (meta)
    if line.startswith("——flag"):
        return ("thought", {"text": line}, current_npc)

    # 7. '【第X章完】' → narrator
    if line.startswith("【") and line.endswith("完】"):
        return ("narrator", {"text": line}, current_npc)

    # 8. 单引号/双引号开头的台词 → 用 current_npc
    if line.startswith("'") or line.startswith('"'):
        npc = current_npc[0] if current_npc else "旁白"
        text = line.strip("'\"")
        text, emotion = extract_emotion(text)
        if npc == "旁白":
            return ("narrator", {"text": line}, current_npc)  # 保留原文
        return ("npc", {"name": npc, "text": text, "emotion": emotion}, current_npc)

    # 9. 默认 narrator
    return ("narrator", {"text": line}, current_npc)


def parse_narrative(narrative: str) -> list[tuple[str, dict]]:
    """把 narrative 字符串解析成 sections 列表 (stateful)"""
    raw = narrative.replace("\\n", "\n")
    lines = raw.split("\n")

    sections = []
    current_npc = ["旁白"]
    prev_narrator = [""]

    for line in lines:
        line = line.strip()
        sec_type, kwargs, current_npc = classify_line_st(line, current_npc, prev_narrator)
        if sec_type == "skip":
            continue
        sections.append((sec_type, kwargs))
        # 记录上一行 narrator
        if sec_type == "narrator":
            prev_narrator[0] = kwargs["text"]
        elif sec_type in ("npc", "sound"):
            prev_narrator[0] = ""  # 重置 (因为有具体 NPC)

    return sections


def gen_sections_code(sections: list[tuple[str, dict]]) -> str:
    """生成 narrative_sections=[...] Python 代码"""
    lines = ["        narrative_sections=["]
    for sec_type, kwargs in sections:
        if sec_type == "narrator":
            text = kwargs["text"].replace("'", "\\'")
            lines.append(f"            _narrator('{text}'),")
        elif sec_type == "thought":
            text = kwargs["text"].replace("'", "\\'")
            lines.append(f"            _thought('{text}'),")
        elif sec_type == "npc":
            name = kwargs["name"].replace("'", "\\'")
            text = kwargs["text"].replace("'", "\\'")
            if kwargs.get("emotion"):
                emotion = kwargs["emotion"].replace("'", "\\'")
                lines.append(f"            _npc('{name}', '{text}', emotion='{emotion}'),")
            else:
                lines.append(f"            _npc('{name}', '{text}'),")
        elif sec_type == "sound":
            text = kwargs["sound"].replace("'", "\\'")
            lines.append(f"            _sound('{text}'),")
    lines.append("        ],")
    return "\n".join(lines)


def find_narrative_blocks(src: str):
    """找到所有 narrative=(...) 块"""
    results = []
    pos = 0
    while True:
        m = re.search(r'narrative=\(', src[pos:])
        if not m:
            break
        start = pos + m.start()
        depth = 1
        i = pos + m.end()
        while i < len(src) and depth > 0:
            ch = src[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1
        if depth == 0:
            content = src[pos + m.end(): i - 1]
            results.append((start, i, content))
            pos = i
        else:
            break
    return results


def process_chapter(ch_id: int, path: str, dry_run: bool = True):
    """处理单个章节文件"""
    src = Path(path).read_text(encoding='utf-8')

    blocks = find_narrative_blocks(src)
    print(f"ch{ch_id}: 找到 {len(blocks)} 个 narrative=(...) 块")

    insertions = []
    skipped = 0
    upgraded = 0  # 已迁移但 emotion 升级

    for start, end, content in blocks:
        preceding = src[max(0, start - 1500):start]
        if "narrative_sections=[" in preceding:
            # 已迁移 - 但 v2 没有 emotion, v3 应该有
            skipped += 1
            continue

        sections = parse_narrative(content)
        if len(sections) < 1:
            continue

        code = gen_sections_code(sections)
        insertions.append((start, code + "\n        "))

    print(f"ch{ch_id}: 已迁移 {skipped}, 将插入 {len(insertions)} 处 narrative_sections=[...]")

    # 不实际升级已迁移的 (避免双重 narrative_sections)
    new_src = src
    insertions.sort(reverse=True)
    for pos, code in insertions:
        new_src = new_src[:pos] + code + new_src[pos:]

    if not dry_run:
        Path(path).write_text(new_src, encoding='utf-8')
        print(f"ch{ch_id}: 已写入 {path}")
    else:
        print(f"ch{ch_id}: DRY RUN, 不写入")

    return new_src, len(insertions)


def main():
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv

    total = 0
    for ch_id, path in CHAPTERS.items():
        _, n = process_chapter(ch_id, path, dry_run=dry_run)
        total += n

    print(f"\n合计迁移 {total} 节点")
    print(f"模式: {'DRY RUN' if dry_run else 'WRITE'}")


if __name__ == "__main__":
    main()