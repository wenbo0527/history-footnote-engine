"""🆕 v2.10.33 P0-1 验证：剧本模式自由输入未匹配不再静默

覆盖：
1. 完全不匹配的输入 → info.no_match=True + match_attempted 原样保留
2. 完全不匹配的输入 → state 不前进（node_id 不变）
3. 完全不匹配的输入 → 仍返回当前节点的 voice_options（玩家可重选）
4. 完全不匹配的输入 → suggested_options 给出可用选项
5. 精确匹配 → info.no_match=False（无误伤）
6. 模糊匹配 → info.no_match=False（无误伤）
7. 重复未匹配（同一输入）→ 仍返回 no_match 信号（前端按 match_attempted 去重）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from history_footnote.story_mode import get_engine
from history_footnote.story_mode.chapter_loader import get_chapter


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def main():
    engine = get_engine()
    # 用第 1 章做测试（最稳定的样本）
    chapter = get_chapter(1)
    engine.chapter = chapter
    engine._chapter_id = chapter.chapter_id

    # 构造游戏状态：进入第一个节点
    state = {
        "scripted_mode": True,
        "scripted_chapter_id": 1,
        "scripted_node_id": chapter.start_node_id,
        "scripted_flags": [],
        "scripted_visits": [chapter.start_node_id],
        "scripted_chapter_complete": False,
        "cash": 1.2,
        "debt": 0.0,
    }
    engine.ensure_state(state)

    start_node = chapter.nodes[chapter.start_node_id]
    real_options = [o.voice_id for o in start_node.voice_options]
    if not real_options:
        print(f"  ❌ 起始节点 {chapter.start_node_id} 没有 voice_options，跳过测试")
        sys.exit(1)
    print(f"  · 起始节点 {chapter.start_node_id}: {len(real_options)} 选项 {real_options[:3]}...\n")

    # 1. 完全不匹配的输入
    print("[1/7] 完全不匹配的输入 → no_match=True")
    bad_input = "乱码随机xyz123我也不知道要干嘛"
    narr1, opts1, info1 = engine.handle_input(state, bad_input)
    ok1 = _step(
        "no_match == True",
        info1.get("no_match") is True,
        f"got {info1.get('no_match')}",
    )
    ok2 = _step(
        "match_attempted 原样保留",
        info1.get("match_attempted") == bad_input,
    )
    ok3 = _step(
        "narrative 顶部含【未识别】提示",
        "【未识别】" in narr1,
    )
    ok4 = _step(
        "state 不前进（scripted_node_id 不变）",
        state.get("scripted_node_id") == chapter.start_node_id,
    )
    ok5 = _step(
        "仍返回当前节点 voice_options",
        len(opts1) == len(real_options),
        f"got {len(opts1)}, expected {len(real_options)}",
    )
    ok6 = _step(
        "suggested_options 非空",
        len(info1.get("suggested_options", [])) > 0,
    )
    ok7 = _step(
        "suggested_options[0] 含 voice_id",
        "voice_id" in (info1.get("suggested_options", [{}])[0] or {}),
    )
    ok8 = _step(
        "effects_applied 为空（未应用）",
        info1.get("effects_applied") == {},
    )
    section1_ok = all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8])

    # 2. 重复未匹配（同一输入第二次）
    print("\n[2/7] 重复未匹配（同一输入第二次）→ 仍返回 no_match")
    narr2, opts2, info2 = engine.handle_input(state, bad_input)
    ok = _step(
        "no_match 仍为 True",
        info2.get("no_match") is True,
    )
    ok = _step(
        "match_attempted 仍为同一字符串",
        info2.get("match_attempted") == bad_input,
    ) and ok
    section2_ok = ok

    # 3. 精确匹配 → 前进，no_match=False
    print("\n[3/7] 精确匹配 → 前进，no_match=False")
    # 找到一个有效选项（取第一个真实 voice_id）
    valid_vid = real_options[0]
    state_before = dict(state)  # shallow copy
    narr3, opts3, info3 = engine.handle_input(state, valid_vid)
    ok = _step(
        "no_match == False",
        info3.get("no_match") is False,
    )
    ok = _step(
        "state 前进（scripted_node_id 改变）",
        state.get("scripted_node_id") != state_before.get("scripted_node_id"),
    ) and ok
    section3_ok = ok

    # 4. 模糊匹配：子串匹配 → no_match=False
    print("\n[4/7] 模糊匹配（子串）→ no_match=False")
    # 回到起始节点
    state["scripted_node_id"] = chapter.start_node_id
    state["scripted_visits"] = [chapter.start_node_id]
    # 选一个 voice_id 的子串（前 4 个字符）
    if len(valid_vid) >= 5:
        substring = valid_vid[:4]
        narr4, opts4, info4 = engine.handle_input(state, substring)
        ok = _step(
            "子串匹配 no_match == False",
            info4.get("no_match") is False,
        )
    else:
        ok = _step("跳过：voice_id 长度 < 5", True, detail="trivially pass")
    section4_ok = ok

    # 5. 中文关键词模糊匹配
    print("\n[5/7] 中文关键词模糊匹配 → no_match=False")
    # 取第一个 voice_option 的 voice_name（中文）来反向猜
    vo = start_node.voice_options[0]
    sample_zh = ""
    for s in [vo.voice_name, vo.description or "", getattr(vo, "inner_voice", "") or ""]:
        if any('\u4e00' <= c <= '\u9fff' for c in s):
            for c in s:
                if '\u4e00' <= c <= '\u9fff' and c not in "的我你他她它吗呢啊吧了的也是就不很都和与及或":
                    sample_zh += c
                    break
            if sample_zh:
                break
    if sample_zh:
        # state 回到 start
        state["scripted_node_id"] = chapter.start_node_id
        state["scripted_visits"] = [chapter.start_node_id]
        narr5, opts5, info5 = engine.handle_input(state, sample_zh)
        ok = _step(
            f"中文「{sample_zh}」模糊匹配 no_match == False",
            info5.get("no_match") is False,
        )
    else:
        ok = _step("跳过：起始节点选项不含中文", True, detail="trivially pass")
    section5_ok = ok

    # 6. 纯标点输入 → 仍属 no_match
    print("\n[6/7] 纯标点输入 → no_match=True")
    state["scripted_node_id"] = chapter.start_node_id
    state["scripted_visits"] = [chapter.start_node_id]
    narr6, opts6, info6 = engine.handle_input(state, "???!!!")
    ok = _step(
        "no_match == True",
        info6.get("no_match") is True,
    )
    section6_ok = ok

    # 7. 后端 router 响应包含 no_match 字段（验证路由层也透传）
    print("\n[7/7] router 透传 no_match（静态检查 routers/input.py）")
    router_src = (ROOT / "src/history_footnote/web_server/routers/input.py").read_text(encoding="utf-8")
    has_no_match = '"no_match": info.get("no_match"' in router_src
    has_match_attempted = '"match_attempted": info.get("match_attempted"' in router_src
    ok = _step(
        "routers/input.py 透传 no_match",
        has_no_match,
    )
    ok = _step(
        "routers/input.py 透传 match_attempted",
        has_match_attempted,
    ) and ok
    section7_ok = ok

    print("\n=== 汇总 ===")
    all_ok = all([section1_ok, section2_ok, section3_ok, section4_ok, section5_ok, section6_ok, section7_ok])
    if all_ok:
        print("🎉 P0-1 全部 7 组测试通过")
        sys.exit(0)
    else:
        print(f"❌ 失败: section1={section1_ok} section2={section2_ok} section3={section3_ok} section4={section4_ok} section5={section5_ok} section6={section6_ok} section7={section7_ok}")
        sys.exit(1)


if __name__ == "__main__":
    print("=== v2.10.33 P0-1 剧本模式自由输入兜底 ===\n")
    main()