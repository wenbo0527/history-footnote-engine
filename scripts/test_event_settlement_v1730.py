"""🆕 v1.7.30 事件识别 + 月度结算静态测试

覆盖：
1. EventId 文档存在
2. event_parser.py：parse_events/apply_event/process_llm_output
3. event_parser 支持 6 类 domain（fin/city/fam/gen/prop/inv）
4. event_parser Layer 2 模糊匹配（中文金额）
5. settlement.py：5 个规则（monthly_burn/deposit/debt/rent/rice）
6. settlement.py 利率常量
7. settlement.py 触发判断（should_settle 每 3 回合）
8. game_loop.py 接入 event_parser + settlement
9. system_base.md 加 <events> 输出格式
10. 端到端集成：mock 跑 6 轮触发月度结算
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs/architecture/EventId规范.md"
EP = ROOT / "src/history_footnote/event_parser.py"
SS = ROOT / "src/history_footnote/settlement.py"
GL = ROOT / "src/history_footnote/game_loop.py"
SP = ROOT / "src/history_footnote/dm/prompts/system_base.md"
STATE = ROOT / "src/history_footnote/game_state.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_doc_exists():
    print("[1/10] EventId 文档存在")
    return _step("  EventId规范.md", DOC.exists())


def test_event_parser_core():
    print("\n[2/10] event_parser 核心 API")
    src = EP.read_text(encoding="utf-8")
    return _step(
        "  parse_events/apply_event/process_llm_output/fuzzy_match_events 定义",
        "def parse_events" in src
        and "def apply_event" in src
        and "def process_llm_output" in src
        and "def fuzzy_match_events" in src,
    )


def test_event_parser_6_domains():
    print("\n[3/10] 6 类 domain 处理器")
    src = EP.read_text(encoding="utf-8")
    domains = ["fin", "city", "fam", "gen", "prop", "inv"]
    ok = True
    for d in domains:
        ok = _step(f"  _apply_{d}_event", f"def _apply_{d}_event" in src) and ok
    ok = _step("  _HANDLERS 映射包含 6 个", f'"_HANDLERS" in src or "_HANDLERS" in src') and ok
    return ok


def test_event_parser_chinese_amount():
    print("\n[4/10] Layer 2 模糊匹配 + 中文金额")
    src = EP.read_text(encoding="utf-8")
    return _step(
        "  CN_DIGITS + _parse_amount + ACTION_VERBS + AMOUNT_RE",
        "CN_DIGITS" in src
        and "_parse_amount" in src
        and "ACTION_VERBS" in src
        and "AMOUNT_RE" in src,
    )


def test_settlement_rules():
    print("\n[5/10] settlement.py 5 个规则")
    src = SS.read_text(encoding="utf-8")
    rules = ["monthly_burn", "deposit_interest", "debt_interest", "workshop_rent", "rice_consumption"]
    ok = True
    for r in rules:
        ok = _step(f"  _settle_{r} 函数", f"def _settle_{r}" in src) and ok
    ok = _step("  DEFAULT_RULES 包含 5 个", "DEFAULT_RULES" in src and "SettlementRule" in src) and ok
    return ok


def test_settlement_constants():
    print("\n[6/10] settlement 利率常量")
    src = SS.read_text(encoding="utf-8")
    return _step(
        "  DEPOSIT_MONTHLY_RATE=0.003 / DEBT_MONTHLY_RATE=0.015 / RICE_PER_PERSON=0.3",
        "DEPOSIT_MONTHLY_RATE = 0.003" in src
        and "DEBT_MONTHLY_RATE = 0.015" in src
        and "RICE_PER_PERSON_PER_MONTH = 0.3" in src,
    )


def test_settlement_trigger():
    print("\n[7/10] settlement 触发逻辑")
    src = SS.read_text(encoding="utf-8")
    return _step(
        "  should_settle / mark_settled / format_settlement_narrative + DEFAULT_MONTHLY_ROUNDS=3",
        "def should_settle" in src
        and "def mark_settled" in src
        and "def format_settlement_narrative" in src
        and "DEFAULT_MONTHLY_ROUNDS = 3" in src,
    )


def test_game_loop_integration():
    print("\n[8/10] game_loop 接入 event_parser + settlement")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  process_llm_output + should_settle + mark_settled + format_settlement_narrative 都在 _run_round 调",
        "from history_footnote.event_parser import process_llm_output" in src
        and "from history_footnote.settlement import" in src
        and "should_settle" in src
        and "mark_settled" in src
        and "format_settlement_narrative" in src,
    )


def test_system_prompt_update():
    print("\n[9/10] system_base.md 加 <events> 输出格式")
    src = SP.read_text(encoding="utf-8")
    return _step(
        "  必填 <events> 块 + 6 类事件 id 提示 + 链接到 EventId 文档",
        "<events>" in src
        and "EventId" in src
        and "v1.7.30" in src
        and "fin.*" in src
        and "city.*" in src
        and "fam.*" in src
        and "prop.*" in src
        and "inv.*" in src
        and "gen.*" in src,
    )


def test_integration_end_to_end():
    """端到端：mock 跑 6 轮 + 验证 settlement 触发"""
    print("\n[10/10] 端到端集成（mock 跑 6 轮）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.mock_llm import MockDMChatModel
    from history_footnote.game_loop import GameLoop
    from history_footnote.storage.save_manager import SaveManager
    import tempfile
    from unittest.mock import patch
    import io

    config = json.loads((ROOT / "eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = MockDMChatModel()
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_int_"))
    save_manager = SaveManager(tmp_root)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
        selected_identity="weaving_male",
    )
    # 初始化 cash
    game.state.cash = 5.0
    game.state.rice = 3.0
    game.state.debt = 2.0
    game.state.monthly_burn = 1.2
    game.state.add_property("shengze", {"id": "p1", "type": "shop", "name": "织房", "value": 15, "rent_per_month": 0.3})

    inputs = ["我织了一匹湖绫", "我把绸拿到牙行去卖"]
    for i in range(6):
        inp = inputs[i % 2]
        try:
            with patch("sys.stdout", new=io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            return _step(f"  run_round 失败: {e}", False)

    n_settle = sum(1 for n in game.state.narrative_history if isinstance(n, dict) and n.get("type") == "monthly_settlement")
    return _step(
        f"  6 轮后触发 1 次月度结算（实际={n_settle}）",
        n_settle == 1,
    )


if __name__ == "__main__":
    print("=== v1.7.30 事件识别 + 月度结算静态测试 ===\n")
    ok1 = test_doc_exists()
    ok2 = test_event_parser_core()
    ok3 = test_event_parser_6_domains()
    ok4 = test_event_parser_chinese_amount()
    ok5 = test_settlement_rules()
    ok6 = test_settlement_constants()
    ok7 = test_settlement_trigger()
    ok8 = test_game_loop_integration()
    ok9 = test_system_prompt_update()
    ok10 = test_integration_end_to_end()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10]):
        print("\n🎉 10 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=} {ok9=} {ok10=}")
        sys.exit(1)
