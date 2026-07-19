"""Wiki集成验证——DM叙事中是否出现narrative_snippet引用"""
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    print("=" * 60)
    print("Wiki 集成验证（narrative_snippets 融合）")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    print(f"\n知识条目: {len(config['knowledge']['entries'])}条")
    print(f"闲谈片段: {len(config['knowledge']['narrative_snippets'])}条")

    from history_footnote.storage.save_manager import SaveManager
    from history_footnote.mock_llm import MockDMChatModel
    from history_footnote.game_loop import GameLoop
    from history_footnote.knowledge_base import KnowledgeBase

    # === 测试1：直接验证KnowledgeBase能查到snippets ===
    print("\n[1] 验证KnowledgeBase.query_snippets")
    kb = KnowledgeBase(
        entries=config["knowledge"]["entries"],
        snippets=config["knowledge"]["narrative_snippets"],
    )
    print(f"  snippets_by_id 数: {len(kb.snippets_by_id)}")
    assert len(kb.snippets_by_id) >= 16, f"应至少16个snippets，实际{len(kb.snippets_by_id)}"

    # 按场景查
    snips_teahouse = kb.query_snippets(scene="茶馆", top_k=3)
    print(f"  场景='茶馆' 命中 {len(snips_teahouse)} 条:")
    for s in snips_teahouse:
        print(f"    - {s['id']}: {s['source'][:30]}")

    snips_market = kb.query_snippets(scene="盛泽市集", top_k=3)
    print(f"  场景='盛泽市集' 命中 {len(snips_market)} 条:")
    for s in snips_market:
        print(f"    - {s['id']}: {s['source'][:30]}")

    snips_yahang = kb.query_snippets(scene="牙行", top_k=3)
    print(f"  场景='牙行' 命中 {len(snips_yahang)} 条:")
    for s in snips_yahang:
        print(f"    - {s['id']}: {s['source'][:30]}")

    # === 测试2：自动场景检测 ===
    print("\n[2] 验证detect_scene自动检测")
    tests = [
        ("我去茶馆坐坐", "茶馆"),
        ("我去集市看看丝价", "盛泽市集"),
        ("去牙行卖绸", "牙行"),
        ("在家里织机前", "自家作坊"),
        ("我听说赵里长来了", "县衙"),
        ("今天随便", ""),
    ]
    for text, expected in tests:
        detected = kb.detect_scene(text)
        status = "✅" if detected == expected else "❌"
        print(f"  {status} '{text}' → '{detected}' (期望 '{expected}')")

    # === 测试3：主循环跑4个回合，每个回合用不同场景，验证snippet被引用 ===
    print("\n[3] 主循环4回合，每回合不同场景")
    save_manager = SaveManager()
    llm = MockDMChatModel(era_config=config)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
    )

    # 4个回合，每个用不同场景
    test_inputs = [
        "我去茶馆坐坐",  # round 1: 茶馆
        "我去集市看看丝绸",  # round 2: 盛泽市集
        "去牙行卖绸",  # round 3: 牙行
        "我盘算着是不是该添置织机",  # round 4: 织机（自家作坊）
        "/state",
        "/quit",
    ]

    captured_narratives = []
    import io
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    try:
        with patch("builtins.input", side_effect=test_inputs):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old_stdout
        output = captured_output.getvalue()

    # 检查输出中是否出现snippet引用
    snippet_ids = [s["id"] for s in config["knowledge"]["narrative_snippets"]]
    found_snippets = []
    for sid in snippet_ids:
        if sid in output:
            found_snippets.append(sid)
    print(f"  4回合中出现的snippet id:")
    for sid in found_snippets:
        print(f"    - {sid}")

    # 检查是否有sn_canshen_temple（小满祭祀）或sn_shishi_shifu_market（盛泽丝市）等
    if "sn_shishi_shifu_market" in output:
        print("  ✅ 盛泽市集场景出现sn_shishi_shifu_market（《醒世恒言》盛泽丝市）")
    if "sn_canshen_temple" in output:
        print("  ✅ 出现sn_canshen_temple（先蚕祠小满祭祀）")

    print("\n" + "=" * 60)
    print("✅ Wiki 集成验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
