"""🆕 v2.10.29 — 自动批量迁移 narrative 字符串 → narrative_sections (实用版)

策略: 解析每个 narrative=(...) 字符串, 启发式分类每行, 生成 narrative_sections Python 表达式

启发式分类:
- 「」开头 → _thought
- 'XX道：' / 'XX说：' / 'XX问：' → _npc
- 'XX：' 开头 (简短 NPC 名) → _npc
- 含 '【XXX】' → npc (特殊)
- 含拟声词 → _sound (无文本)
- '——flag' 开头 → _thought
- 默认 → _narrator

输出: 修改 chapter_XX.py 文件, 在 narrative= 上方插入 narrative_sections=[...]
"""
import re
import sys
from pathlib import Path

CHAPTERS = {
    1: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_01.py',
    2: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_02.py',
    3: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_03.py',
}


# NPC 词典 (按 NPC 名映射)
KNOWN_NPCS = {
    "张氏", "父亲", "父亲沈茂", "钱老板", "钱少", "周大娘", "张叔", "赵师傅",
    "孙掌柜", "掌柜", "王掌柜", "王婆", "陈小", "陈师傅", "李保", "太监", "太监李保",
    "周七", "刘二", "宋明", "王公", "母亲", "牙行掌柜", "白头翁", "税关",
    "苏州恒德祥", "内衙",
}


def classify_line(line: str) -> tuple[str, dict]:
    """启发式分类一行"""
    line = line.strip()
    if not line:
        return ("skip", {})

    # 1. 「...」开头 → thought
    if line.startswith("「"):
        inner = line.lstrip("「").rstrip("」").rstrip("。")
        return ("thought", {"text": inner})

    # 2. 'XX道：' / 'XX说：' 等动词 → npc
    m = re.match(
        r"^([\u4e00-\u9fa5·]{1,8})(道|说|叹|应|答|笑|问|喊|低声道|笑着说|低声|回答|轻声说)[:：]\s*(.+)",
        line,
    )
    if m:
        return ("npc", {"name": m.group(1), "text": m.group(3), "emotion": ""})

    # 3. 'XX：' 开头 (NPC 名) → npc
    m = re.match(r"^([\u4e00-\u9fa5·]{1,8})[:：]\s*(.+)$", line)
    if m:
        name = m.group(1)
        # 已知 NPC 名 OR 1-4 字符中文 → npc
        if name in KNOWN_NPCS or (1 <= len(name) <= 4 and "·" not in line):
            # 排除 narrator 描述 (e.g. "父亲心里藏着的秘密：...")
            text = m.group(2)
            if "：" not in text:
                # 去除文本外的引号
                text = text.strip("'\"")
                return ("npc", {"name": name, "text": text, "emotion": ""})

    # 4. 【XXX】前缀 → npc
    m = re.match(r"^【([\u4e00-\u9fa5·]{1,8})】\s*(.+)", line)
    if m:
        return ("npc", {"name": m.group(1), "text": m.group(2), "emotion": ""})

    # 5. 含拟声词 → sound
    soundeffects = ["咚", "咳", "嘶", "哗", "嗡", "鸣", "沙沙", "呼呼", "噼啪", "吱呀", "扑通", "咕嘟", "砰砰", "叮", "唰", "呜", "啪", "踢踏", "咯咯", "唰唰", "唢呐"]
    for se in soundeffects:
        if se in line:
            return ("sound", {"sound": line})

    # 6. '——flag' → thought (meta)
    if line.startswith("——flag"):
        return ("thought", {"text": line})

    # 7. '【第一章完】' / '【第二章完】' → narrator
    if line.startswith("【") and line.endswith("完】"):
        return ("narrator", {"text": line})

    # 8. 单引号/双引号开头的台词 → thought (保留作为内心引用)
    # 注意: 这类前面通常是 NPC 的 'XX道：' 或 'XX：' 已被规则 2/3 处理
    if line.startswith("'") or line.startswith('"'):
        text = line.strip("'\"")
        return ("narrator", {"text": line})  # 保持引号原文

    # 9. 默认 narrator
    return ("narrator", {"text": line})


def parse_narrative(narrative: str) -> list[tuple[str, dict]]:
    """把 narrative 字符串解析成 sections 列表

    Args:
        narrative: 原始字符串, 可能含 \\n 字面量 (Python 源代码风格)
    """
    # 将源代码风格的 \\n 转为真实换行
    raw = narrative.replace("\\n", "\n")
    sections = []
    lines = raw.split("\n")

    for line in lines:
        line = line.strip()
        sec_type, kwargs = classify_line(line)
        if sec_type == "skip":
            continue
        sections.append((sec_type, kwargs))

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
            lines.append(f"            _npc('{name}', '{text}'),")
        elif sec_type == "sound":
            text = kwargs["sound"].replace("'", "\\'")
            lines.append(f"            _sound('{text}'),")
    lines.append("        ],")
    return "\n".join(lines)


def find_narrative_blocks(src: str):
    """找到所有 narrative=(...) 块 (含跨行)

    返回: [(start_pos, end_pos, content), ...]
    """
    results = []
    pos = 0
    while True:
        m = re.search(r'narrative=\(', src[pos:])
        if not m:
            break
        start = pos + m.start()
        # 从 ( 后开始匹配括号配对
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

    # 找到所有 narrative=(...) 块
    blocks = find_narrative_blocks(src)
    print(f"ch{ch_id}: 找到 {len(blocks)} 个 narrative=(...) 块")

    # 排除已经有 narrative_sections 的 (其前一行是 narrative_sections=[)
    # 检查范围扩大到 1500 字符 (覆盖 narrative_sections=[...] 整个 block)
    new_src = src
    insertions = []  # [(insert_pos, code), ...]
    skipped = 0
    for start, end, content in blocks:
        # 看前面 1500 字符是否有 narrative_sections=[ (本节点已迁移)
        preceding = src[max(0, start - 1500):start]
        if "narrative_sections=[" in preceding:
            skipped += 1
            continue  # 已迁移

        # 解析 content
        sections = parse_narrative(content)
        if len(sections) < 1:
            continue

        # 生成代码
        code = gen_sections_code(sections)

        # 找到 narrative= 的开始 (start 位置), 在前面插入
        # 但要确保缩进对齐
        insertions.append((start, code + "\n        "))  # 加回 narrative= 行的缩进

    print(f"ch{ch_id}: 已迁移 {skipped}, 将插入 {len(insertions)} 处 narrative_sections=[...]")

    # 倒序插入 (避免位置偏移)
    insertions.sort(reverse=True)
    for pos, code in insertions:
        new_src = new_src[:pos] + code + new_src[pos:]

    # 写入
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