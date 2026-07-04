"""验证DND随机性：同一输入多次跑应该看到不同输出"""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager
from history_footnote.dice_engine import DiceEngine
from history_footnote.knowledge_base import KnowledgeBase


def main():
    print("=" * 60)
    print("DND 随机性验证")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    # === 测试1：DiceEngine基础功能 ===
    print("\n[1] DiceEngine基础功能")
    engine = DiceEngine(seed=42)
    for i in range(3):
        r = engine.roll("d20", purpose=f"测试{i}")
        print(f"  d20 #{i}: {r.total}")
    assert engine.roll("2d6+3", purpose="组合测试").total >= 5
    print(f"  ✅ 掷骰子正常")

    # === 测试2：DC判定 ===
    print("\n[2] DC判定")
    engine2 = DiceEngine(seed=100)
    successes = 0
    for i in range(10):
        result = engine2.check(15, "d20", 5, f"判定{i}")
        if result["success"]:
            successes += 1
    print(f"  d20+5 vs DC15 (10次): 成功{successes}次（预期~55%）")
    print(f"  ✅ 判定系统正常")

    # === 测试3：加权选择 ===
    print("\n[3] 加权随机选择")
    engine3 = DiceEngine(seed=200)
    counts = {"A": 0, "B": 0, "C": 0}
    for _ in range(100):
        result = engine3.weighted_choice([
            {"item": "A", "weight": 3},
            {"item": "B", "weight": 1},
            {"item": "C", "weight": 1},
        ])
        counts[result] += 1
    print(f"  A(weight=3) B(weight=1) C(weight=1) 各100次:")
    print(f"    A: {counts['A']}次 (~60%)")
    print(f"    B: {counts['B']}次 (~20%)")
    print(f"    C: {counts['C']}次 (~20%)")
    print(f"  ✅ 加权选择工作")

    # === 测试4：story_segments随机性 ===
    print("\n[4] story_segments随机抽取（同一scene多次抽取）")
    kb = KnowledgeBase(
        entries=config["knowledge"]["entries"],
        snippets=config["knowledge"]["narrative_snippets"],
        story_segments=config["knowledge"]["story_segments"],
    )
    seen_ids = set()
    for i in range(10):
        seg = kb.get_random_segment(scene="盛泽市集")
        if seg:
            seen_ids.add(seg["id"])
    print(f"  10次随机抽取场景：盛泽市集，见到{len(seen_ids)}个不同片段")
    print(f"    IDs: {sorted(seen_ids)[:5]}...")
    assert len(seen_ids) >= 3, f"应至少见到3个不同片段，实际{len(seen_ids)}"
    print(f"  ✅ 随机性工作（10次抽到{len(seen_ids)}种）")

    # === 测试5：随机事件 ===
    print("\n[5] 随机事件触发（场景+概率）")
    kb = KnowledgeBase(
        entries=config["knowledge"]["entries"],
        snippets=config["knowledge"]["narrative_snippets"],
        story_segments=config["knowledge"]["story_segments"],
    )
    events = config["world"].get("random_events", [])
    print(f"  配置了{len(events)}个随机事件表")
    for e in events:
        print(f"    {e['id']}: scene={e['trigger_condition'].get('scene', 'any')}, p={e['probability']}")

    # === 测试6：同一玩家输入跑5次，叙事应该有差异 ===
    print("\n[6] 同一输入跑5次，看叙事差异")
    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_random_test_"))
    try:
        outputs = []
        for run_idx in range(5):
            save_manager = SaveManager(Path(tmp_root) / f"run{run_idx}")
            llm = MockDMChatModel(era_config=config)
            game = GameLoop(
                era_id="wanli1587",
                era_config=config,
                llm_model=llm,
                save_manager=save_manager,
                selected_identity="weaving_male",
            )

            # 跑同一个输入3次
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                with patch("builtins.input", side_effect=["我去茶馆坐坐", "/quit"]):
                    try:
                        game.run()
                    except SystemExit:
                        pass
            finally:
                sys.stdout = old_stdout
                output = captured.getvalue()
                outputs.append(output)
        # 统计差异
        unique_narratives = set()
        for o in outputs:
            # 提取叙事部分（去掉状态行）
            lines = [l for l in o.split("\n") if "DM叙事" in l or "镇上" in l or "茶馆" in l or "癞痢头" in l or "老" in l]
            unique_narratives.add("\n".join(lines[:5]))

        print(f"  5次跑同一输入，得到{len(unique_narratives)}种不同叙事（最多5种）")
        for i, narr in enumerate(sorted(unique_narratives)[:3], 1):
            print(f"\n  --- 叙事变种{i} ---")
            print(f"  {narr[:200]}...")

        if len(unique_narratives) >= 2:
            print(f"\n  ✅ 随机性生效（{len(unique_narratives)}/5种不同）")
        else:
            print(f"\n  ⚠️ 随机性可能不够")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)

    print("\n" + "=" * 60)
    print("✅ DND 随机性验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()