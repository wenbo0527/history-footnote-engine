"""🆕 v2.10.30 — 给已迁移的 narrative_sections 补充 emotion

策略:
- 找到 narrative_sections=[...] 块
- 对每个 _npc(name, text) 调用, 尝试从 text 推断 emotion
- 规则:
  - text 含 (忧)/(喜)/(惊恐)/(气弱) → 用括号内文字
  - text 含 涨红了脸/满脸通红/面如金纸/攥紧/气喘 → emotion = "悲"
  - text 含 笑/点头/赞许 → emotion = "喜"
  - text 含 怒/瞪眼/皱眉/为难 → emotion = "怒"
"""
import re
import sys
from pathlib import Path

CHAPTERS = {
    1: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_01.py',
    2: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_02.py',
    3: '/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/chapter_03.py',
}


EMOTION_RULES = [
    # (regex, emotion)
    (r"（忧）|（愁）|（哀）", "忧"),
    (r"（喜）|（面有喜色）", "喜"),
    (r"（怒）|（瞪眼）|（皱眉）|（为难）|（阴沉）", "怒"),
    (r"（惊恐）|（恐惧）|（惊恐）", "惊恐"),
    (r"（苦笑）|（叹气）|（摇头）|（皱眉）", "苦笑"),
    (r"（笑）|（点头）|（赞许）|（惊叹）", "喜"),
    (r"（气弱）|（喘）", "气弱"),
    (r"（激昂）|（激）", "激昂"),
    (r"（郑重）|（正色）", "郑重"),
    (r"（神秘）|（压低声音）", "神秘"),
    (r"（假笑）", "假笑"),
    (r"（涨红了脸）|（满脸通红）", "涨红了脸"),
]


def infer_emotion(text: str) -> str:
    """从 text 推断 emotion"""
    for pattern, emotion in EMOTION_RULES:
        if re.search(pattern, text):
            return emotion
    return ""


def upgrade_sections(src: str) -> tuple[str, int]:
    """升级 narrative_sections 中所有 _npc 调用的 emotion

    返回: (新 src, 升级次数)
    """
    upgrade_count = 0

    # 找到所有 _npc('XXX', 'YYY') 模式 (无 emotion)
    # 不替换已有 emotion= 的
    pattern = re.compile(r"_npc\('([^']*)',\s*'([^']*)'\)")

    def repl(m):
        nonlocal upgrade_count
        name = m.group(1)
        text = m.group(2)
        emotion = infer_emotion(text)
        if emotion:
            upgrade_count += 1
            return f"_npc('{name}', '{text}', emotion='{emotion}')"
        return m.group(0)

    new_src = pattern.sub(repl, src)
    return new_src, upgrade_count


def main():
    dry_run = "--dry-run" in sys.argv

    total = 0
    for ch_id, path in CHAPTERS.items():
        src = Path(path).read_text(encoding='utf-8')
        new_src, count = upgrade_sections(src)
        print(f"ch{ch_id}: 升级 {count} 处 _npc 调用")
        total += count
        if not dry_run and count > 0:
            Path(path).write_text(new_src, encoding='utf-8')
            print(f"  已写入")

    print(f"\n合计升级 {total} 处")
    print(f"模式: {'DRY RUN' if dry_run else 'WRITE'}")


if __name__ == "__main__":
    main()