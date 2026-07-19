"""存档与重开功能验证脚本

测试流程：
1. 跑3个回合（产生auto.json + slot1）
2. 验证存档目录结构
3. 列出所有存档
4. 从slot1读档，跑2回合
5. 删除session
6. 验证saves/被清空
"""
import json
import sys
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    # 使用临时目录作为saves根目录，避免污染
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_test_saves_"))
    print(f"使用临时存档目录: {tmp_root}")

    try:
        from history_footnote.storage.save_manager import SaveManager
        from history_footnote.mock_llm import MockDMChatModel
        from history_footnote.game_loop import GameLoop

        # 加载时代包
        config = json.loads(
            Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
        )

        # === 第1步：跑3个回合，存到slot1 ===
        print("\n[1] 跑3个回合...")
        save_manager = SaveManager(tmp_root)
        llm = MockDMChatModel(era_config=config)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
        )
        session = game.session
        print(f"  session: {session.session_id}")
        print(f"  初始回合: {game.state.round_number}")

        # 模拟玩家输入：3个回合 + /save 1 + /state + /quit
        test_inputs = [
            "我在织机前理经线",
            "我去茶馆坐坐",
            "我打听一下丝绸的事",
            "/save 1",
            "/state",
            "/quit",
        ]
        with patch("builtins.input", side_effect=test_inputs):
            try:
                game.run()
            except SystemExit:
                pass

        # === 第2步：验证存档目录结构 ===
        print("\n[2] 验证存档目录结构")
        session_dir = tmp_root / session.session_id
        print(f"  session_dir: {session_dir}")
        print(f"  目录存在: {session_dir.is_dir()}")
        for f in sorted(session_dir.iterdir()):
            print(f"    {f.name}: {f.stat().st_size} bytes")

        # 验证meta.json + auto.json + slot1.json
        assert (session_dir / "meta.json").exists(), "meta.json不存在"
        assert (session_dir / "auto.json").exists(), "auto.json不存在"
        assert (session_dir / "slot1.json").exists(), "slot1.json不存在"

        # 验证meta内容
        meta = json.loads((session_dir / "meta.json").read_text(encoding="utf-8"))
        print(f"  meta.session_id: {meta['session_id']}")
        print(f"  meta.current_round: {meta['current_round']}")
        print(f"  meta.current_date: {meta['current_date']}")
        assert meta["current_round"] >= 3, f"进度应>=3，实际{meta['current_round']}"

        # 验证auto.json内容
        auto = json.loads((session_dir / "auto.json").read_text(encoding="utf-8"))
        assert auto["round_number"] == meta["current_round"], "auto和meta进度不一致"
        assert "event_log" in auto, "auto.json应包含event_log"
        assert len(auto["event_log"]) >= 3, f"event_log应>=3条，实际{len(auto['event_log'])}"

        # === 第3步：从slot1读档，验证state恢复 ===
        print("\n[3] 从slot1读档，跑2回合")
        slot1_data = json.loads((session_dir / "slot1.json").read_text(encoding="utf-8"))
        print(f"  slot1 round: {slot1_data['round_number']}")
        print(f"  slot1 event_log: {len(slot1_data['event_log'])}条")

        # 重新构造GameLoop用slot1数据
        llm2 = MockDMChatModel(era_config=config)
        game2 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm2,
            save_manager=save_manager,
            session=session,
            load_state_data=slot1_data,
        )
        # 验证state恢复
        assert game2.state.round_number == slot1_data["round_number"], f"state回合数应={slot1_data['round_number']}，实际{game2.state.round_number}"
        assert game2.memory.count() == len(slot1_data["event_log"]), f"记忆数应={len(slot1_data['event_log'])}，实际{game2.memory.count()}"
        print(f"  state.round_number: {game2.state.round_number} ✅")
        print(f"  state.current_date: {game2.state.current_date} ✅")
        print(f"  state.unlocked_insights: {game2.state.unlocked_insights} ✅")
        print(f"  memory.count: {game2.memory.count()} ✅")

        # 跑2回合
        test_inputs2 = [
            "我决定去茶馆继续打听",
            "按时交税",
            "/state",
            "/quit",
        ]
        with patch("builtins.input", side_effect=test_inputs2):
            try:
                game2.run()
            except SystemExit:
                pass

        # === 第4步：验证SaveManager的list_sessions ===
        print("\n[4] 验证list_sessions")
        sessions = save_manager.list_sessions(era_id="wanli1587")
        print(f"  找到 {len(sessions)} 个session")
        assert len(sessions) == 1, f"应有1个session，实际{len(sessions)}"
        for s in sessions:
            print(f"    {s.session_id}: round={s.current_round}, slots={list(s.slots.keys())}")

        # === 第5步：删除session ===
        print("\n[5] 删除session")
        assert save_manager.delete_session(session.session_id), "删除失败"
        assert not session_dir.exists(), "session目录应被删除"
        print(f"  ✅ {session.session_id} 已删除")

        # 验证list_sessions为空
        sessions2 = save_manager.list_sessions()
        assert len(sessions2) == 0, f"删除后应有0个session，实际{len(sessions2)}"
        print(f"  ✅ 列表为空")

        print("\n" + "=" * 60)
        print("✅ 存档与重开功能验证全部通过")
        print("=" * 60)

    finally:
        # 清理临时目录
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
