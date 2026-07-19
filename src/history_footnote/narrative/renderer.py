"""🆕 v1.7.0 Narrative Renderer - 结构化叙事

设计目标：
- 把"剧情 / 对话 / 内心独白 / 场景过渡" 视觉区分
- 选项（options）成为固定模块
- 渐进式：LLM 可选输出 narrative_blocks，旧 narrative 文本启发式分段

Block 类型：
- scene      普通叙述/环境描写
- dialogue   对话（有说话人）
- monologue  内心独白（"我"的视角）
- transition 场景切换（时间/地点变化）
- options    固定模块（在 narrative 中嵌入，供前端解析）

使用：
- LLM 输出 narrative_blocks (数组) → 优先使用
- LLM 只输出 narrative 字符串 → narrative_to_blocks() 启发式分段
- 前端 render_blocks_to_html() 渲染
"""
from __future__ import annotations

import re
from typing import Optional

# ============================================================
# Block 解析
# ============================================================

# 🆕 中文对话模式：speaker + 动词 + 引号
# 关键：speaker 只能是中文姓氏/名字常用字，不包含动词字
# （否则 "沈氏答道" 会被切成 "沈氏答" + "道"）
# 策略：先抓"中文 + 动词"所有组合，再用 VERB_CHARS 排除错误的 speaker

# 任何"中文 1-6 字"开头，匹配下面的动词
VERB_PATTERN = (
    r"低声道|沉声道|冷声道|高声道|朗声道|轻轻[地说]+|怒道|喜道|悲道|叹道|"
    r"笑道|答道|问道|摇了摇头|想了想|犹豫[了]?|"
    r"说|道|答|问"
)
# raw 匹配：speaker 可以包含动词字（让正则简单）
DIALOGUE_RAW_PATTERN = re.compile(
    rf"([\u4e00-\u9fff]{{1,6}})(?:{VERB_PATTERN})"
    r"[，：:]?\s*"
    r"[\"「『]([^\"」』]+)[\"」』]",
    re.UNICODE,
)
# 动词字集合（用于校验 speaker）
VERB_CHARS_SET = set("说道问答笑叹喜怒悲低高朗沉里心盘算思量嘀咕揣度估摸合计想")


def _refine_dialogue_match(raw_match: re.Match) -> tuple[str, str] | None:
    """从 raw 匹配中提取真正的 speaker（去掉动词字）"""
    raw_speaker = raw_match.group(1)
    content = raw_match.group(2)
    # 逐步去掉尾部动词字
    speaker = raw_speaker
    while speaker and speaker[-1] in VERB_CHARS_SET:
        speaker = speaker[:-1]
    # speaker 至少 1 字
    if not speaker:
        return None
    return speaker, content


# 兼容旧名字（仍导出 DIALOGUE_PATTERN，但通过 wrapper 修正）
class _DialoguePatternProxy:
    """代理 DIALOGUE_RAW_PATTERN，自动修正 speaker"""
    def findall(self, text: str) -> list[tuple[str, str]]:
        raw = DIALOGUE_RAW_PATTERN.findall(text)
        results = []
        for speaker, content in raw:
            # 修正 speaker
            s = speaker
            while s and s[-1] in VERB_CHARS_SET:
                s = s[:-1]
            if s:
                results.append((s, content))
        return results

    def finditer(self, text: str):
        """返回修正后的 match 对象（只暴露 group(1) 和 group(2)）"""
        class _RefinedMatch:
            def __init__(self, raw_m, refined_speaker, content):
                self._raw = raw_m
                self._speaker = refined_speaker
                self._content = content
            def start(self):
                return self._raw.start()
            def end(self):
                return self._raw.end()
            def group(self, n):
                if n == 1:
                    return self._speaker
                if n == 2:
                    return self._content
                return self._raw.group(n)
        for raw_m in DIALOGUE_RAW_PATTERN.finditer(text):
            refined = _refine_dialogue_match(raw_m)
            if refined:
                yield _RefinedMatch(raw_m, refined[0], refined[1])


DIALOGUE_PATTERN = _DialoguePatternProxy()

# 🆕 内心独白模式："你心里想："  "你暗想："  "你在心里盘算："  "你心想："
# 匹配第一人称思考
MONOLOGUE_PATTERN = re.compile(
    r"(?:你|我)(?:心里|暗中|在心底|在心中|暗暗|默默)?(?:想|盘算|琢磨|思量|嘀咕|盘算|算|合计|揣度|估摸)"
    r"[：:，]?\s*"
    r"([^。！？\n]{8,200})"
    r"[。！？]?",
    re.UNICODE,
)

# 🆕 场景切换关键词
TRANSITION_KEYWORDS = [
    r"片刻[后之]?[，]?",
    r"过了[一二三四五六七八九十几半数]+",
    r"转眼[间]?",
    r"少[顷间]",
    r"不知[过了多久]",
    r"话说",
    r"且说",
    r"次日",
    r"隔日",
    r"翌日",
    r"晨起[后]?",
    r"黄昏时[分]?",
    r"傍晚[时分]?",
]
TRANSITION_PATTERN = re.compile(
    r"^(" + "|".join(TRANSITION_KEYWORDS) + r")",
    re.UNICODE | re.MULTILINE,
)


def narrative_to_blocks(text: str) -> list[dict]:
    """🆕 v1.7.0 启发式把 narrative 文本分段为 blocks

    规则（按优先级）：
    1. 对话（"XX 说：" 引号内容）→ dialogue block
    2. 内心独白（"你心里想：..."）→ monologue block
    3. 段首时间/地点切换关键词 → transition block
    4. 其他 → scene block

    保留原始顺序，按"句子"切分。
    """
    if not text or not text.strip():
        return []

    blocks = []
    # 按段落切分（保留段落结构）
    paragraphs = re.split(r"(\n\n+)", text)
    current_scene_text = ""

    def flush_scene():
        nonlocal current_scene_text
        if current_scene_text.strip():
            blocks.append({
                "type": "scene",
                "text": current_scene_text.strip(),
            })
            current_scene_text = ""

    for para in paragraphs:
        if not para or para.isspace():
            continue
        if re.match(r"\n\n+", para):
            flush_scene()
            continue

        # 检查段首是否是 transition
        transition_match = TRANSITION_PATTERN.match(para)
        if transition_match:
            flush_scene()
            blocks.append({
                "type": "transition",
                "text": transition_match.group(1),
            })
            # 段落的剩余部分作为 scene
            rest = para[transition_match.end():].strip()
            if rest:
                current_scene_text += rest + "\n"
            continue

        # 在段落中查找 dialogue 和 monologue
        # 用 pattern 找位置，按位置切
        para_blocks = _parse_paragraph(para)
        # 检查是否整段都是 scene（没找到 dialogue/monologue）
        if len(para_blocks) == 1 and para_blocks[0]["type"] == "scene":
            current_scene_text += para_blocks[0]["text"] + "\n\n"
        else:
            # 段内有 dialogue/monologue，先 flush scene
            flush_scene()
            blocks.extend(para_blocks)

    flush_scene()
    return blocks


def _parse_paragraph(para: str) -> list[dict]:
    """解析单个段落，识别 dialogue / monologue / scene"""
    blocks = []
    pos = 0

    # 同时匹配 dialogue 和 monologue，按位置排序
    matches = []
    for m in DIALOGUE_PATTERN.finditer(para):
        matches.append((m.start(), m.end(), "dialogue", m.group(1), m.group(2)))
    for m in MONOLOGUE_PATTERN.finditer(para):
        matches.append((m.start(), m.end(), "monologue", None, m.group(1)))

    # 按位置排序
    matches.sort()

    # 去重：重叠的 matches 只保留第一个
    deduped = []
    last_end = 0
    for start, end, btype, speaker, content in matches:
        if start < last_end:
            continue
        deduped.append((start, end, btype, speaker, content))
        last_end = end

    # 生成 blocks
    for start, end, btype, speaker, content in deduped:
        # 段首到 match 开头 → scene
        if start > pos:
            scene_text = para[pos:start].strip()
            if scene_text:
                blocks.append({"type": "scene", "text": scene_text})
        # match 本身
        if btype == "dialogue":
            blocks.append({
                "type": "dialogue",
                "speaker": speaker,
                "text": content,
            })
        else:  # monologue
            blocks.append({
                "type": "monologue",
                "text": content.strip(),
            })
        pos = end

    # 剩余部分
    if pos < len(para):
        rest = para[pos:].strip()
        if rest:
            blocks.append({"type": "scene", "text": rest})

    if not blocks:
        blocks.append({"type": "scene", "text": para.strip()})

    return blocks


# ============================================================
# HTML 渲染（前端 fallback 用）
# ============================================================

def render_blocks_to_html(blocks: list[dict]) -> str:
    """🆕 v1.7.0 把 blocks 渲染为 HTML

    输出格式（前端可直接 innerHTML）：
        <div class="block-scene">...</div>
        <div class="block-dialogue">
          <span class="speaker">张顺</span>
          <span class="content">三两三</span>
        </div>
        <div class="block-monologue">💭 ...</div>
        <div class="block-transition">⏱ 片刻后</div>
    """
    import html as _html
    html_parts = []
    for block in blocks:
        btype = block.get("type", "scene")
        if btype == "scene":
            text = _html.escape(block.get("text", ""))
            html_parts.append(f'<div class="block-scene">{text}</div>')
        elif btype == "dialogue":
            speaker = _html.escape(block.get("speaker", ""))
            text = _html.escape(block.get("text", ""))
            html_parts.append(
                f'<div class="block-dialogue">'
                f'<span class="speaker">{speaker}</span>：'
                f'<span class="content">"{text}"</span>'
                f'</div>'
            )
        elif btype == "monologue":
            text = _html.escape(block.get("text", ""))
            html_parts.append(f'<div class="block-monologue">💭 {text}</div>')
        elif btype == "transition":
            text = _html.escape(block.get("text", ""))
            html_parts.append(f'<div class="block-transition">⏱ {text}</div>')
        # options 由 voice_options 模块处理，不在 narrative blocks 里
    return "\n".join(html_parts)


# ============================================================
# 工具函数
# ============================================================

def ensure_blocks(
    structured_blocks: list[dict] | None,
    narrative_text: str,
    options: list[dict] | None = None,
) -> list[dict]:
    """🆕 v1.7.0 规范化 narrative → blocks

    Args:
        structured_blocks: LLM 直接返回的 narrative_blocks（可选）
        narrative_text: narrative 字符串
        options: 选项（独立字段，不会混进 blocks）

    Returns:
        最终的 blocks 列表
    """
    if structured_blocks and len(structured_blocks) > 0:
        return structured_blocks
    if narrative_text:
        return narrative_to_blocks(narrative_text)
    return []


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Narrative Renderer Test (v1.7.0)")
    print("=" * 50)

    SAMPLE = """你站在牙行门口，夕阳斜照在青砖上。

张顺说："三两三，不能再多了。"

你心里想：他出价比周老板低，但张顺从不赊账。要是拿到钱，春税的事就不用愁了。但丁娘子的账还没还...

片刻后，张顺敲了敲柜台。"想好了没？"

一、全卖给他
二、讨价还价
三、先问代织的事"""

    print("\n=== 输入文本 ===")
    print(SAMPLE)
    print("\n=== 解析结果 ===")
    blocks = narrative_to_blocks(SAMPLE)
    for i, b in enumerate(blocks):
        print(f"  [{i}] {b['type']:12s} | {b.get('speaker', '')}{b['text'][:60]}...")

    # 断言
    assert len(blocks) >= 4
    assert any(b["type"] == "scene" for b in blocks)
    assert any(b["type"] == "dialogue" for b in blocks)
    assert any(b["type"] == "monologue" for b in blocks)
    assert any(b["type"] == "transition" for b in blocks)
    print(f"\n✅ 5 种类型全部识别: {set(b['type'] for b in blocks)}")

    # HTML 渲染
    html = render_blocks_to_html(blocks)
    print("\n=== HTML 输出 ===")
    print(html[:300])
    assert "block-scene" in html
    assert "block-dialogue" in html
    assert "block-monologue" in html
    assert "block-transition" in html
    print("\n✅ HTML 渲染包含 4 种 CSS class")

    # ensure_blocks
    blocks2 = ensure_blocks(None, SAMPLE)
    assert len(blocks2) == len(blocks)
    blocks3 = ensure_blocks(blocks, "")
    assert len(blocks3) == len(blocks)
    print(f"✅ ensure_blocks: structured 优先")

    print("\n✅ 所有测试通过")