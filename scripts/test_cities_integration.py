"""🆕 v1.7.30 城市集成静态验证

覆盖：
1. era.json 4 城市节点
2. city_entry_events 4 事件
3. game_state.GameState 有 current_city 字段
4. DMAgent._build_current_city_section 方法
5. system_base.md 包含 current_city 占位符 + 城市感知段
6. 文档：城市Wiki.md / 离乡路线Wiki.md / 闲谈素材Wiki.md 都有城市内容
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
ERA = ROOT / "eras" / "wanli1587" / "era.json"
GS = ROOT / "src/history_footnote/game_state.py"
AGENT = ROOT / "src/history_footnote/dm_agent/agent.py"
SYSTEM = ROOT / "src/history_footnote/dm/prompts/system_base.md"
CITY_WIKI = ROOT / "docs/eras/万历十五年/城市Wiki.md"
LI_XIANG = ROOT / "docs/eras/万历十五年/离乡路线Wiki.md"
XIAN_TAN = ROOT / "docs/eras/万历十五年/闲谈素材Wiki.md"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_era_cities():
    print("[1/7] era.json 4 城市节点")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    cities = era.get("world", {}).get("cities", {})
    expected = {"suzhou", "hangzhou", "songjiang", "nanjing"}
    ok = True
    ok = _step("  4 城市存在", set(cities.keys()) == expected) and ok
    for cid, c in cities.items():
        has_keys = all(k in c for k in ("name", "sensory", "functions", "entry_event"))
        ok = _step(f"  {cid} 完整字段（name/sensory/functions/entry_event）", has_keys) and ok
    return ok


def test_city_entry_events():
    print("\n[2/7] city_entry_events 4 事件")
    era = json.loads(ERA.read_text(encoding="utf-8"))
    events = era.get("world", {}).get("city_entry_events", {})
    ok = True
    ok = _step("  4 城市 entry events", set(events.keys()) == {"suzhou", "hangzhou", "songjiang", "nanjing"}) and ok
    for cid, e in events.items():
        has_keys = all(k in e for k in ("event_id", "name", "description", "narrative_hook", "effects"))
        ok = _step(f"  {cid} entry_event 完整字段", has_keys) and ok
    return ok


def test_game_state_current_city():
    print("\n[3/7] game_state.GameState.current_city 字段")
    src = GS.read_text(encoding="utf-8")
    return _step("  current_city: str 字段存在", 'current_city: str = "shengze"' in src)


def test_agent_current_city_method():
    print("\n[4/7] DMAgent._build_current_city_section 方法")
    src = AGENT.read_text(encoding="utf-8")
    has_method = "def _build_current_city_section" in src
    has_logic = "current_city_id = getattr(self.state, \"current_city\", \"\")" in src
    has_return_empty = "return \"\"" in src
    has_sensory = "sight" in src and "sound" in src and "smell" in src
    ok = True
    ok = _step("  方法定义", has_method) and ok
    ok = _step("  从 state.current_city 读取", has_logic) and ok
    ok = _step("  默认返回空字符串（玩家在盛泽）", has_return_empty) and ok
    ok = _step("  包含感官三维度（sight/sound/smell）", has_sensory) and ok
    return ok


def test_system_base_md():
    print("\n[5/7] system_base.md 占位符 + 城市感知段")
    src = SYSTEM.read_text(encoding="utf-8")
    has_placeholder = "{current_city}" in src
    has_zhishi = "城市感知" in src
    has_4_cities = all(c in src for c in ["苏州", "杭州", "松江", "南京"])
    ok = True
    ok = _step("  {current_city} 占位符", has_placeholder) and ok
    ok = _step("  城市感知段（v1.7.30 段标题）", has_zhishi) and ok
    ok = _step("  4 城市都在城市感知段提到", has_4_cities) and ok
    return ok


def test_city_wiki():
    print("\n[6/7] 城市Wiki.md 存在 + 4 城市")
    src = CITY_WIKI.read_text(encoding="utf-8") if CITY_WIKI.exists() else ""
    if not src:
        return _step("  城市Wiki.md 存在", False)
    ok = True
    for cn in ["苏州", "杭州", "松江", "南京"]:
        has = f"## {cn}" in src
        ok = _step(f"  {cn} 章节", has) and ok
    return ok


def test_other_docs_have_city_links():
    print("\n[7/7] 离乡路线Wiki + 闲谈素材Wiki 都有城市内容")
    ok = True
    if LI_XIANG.exists():
        lx = LI_XIANG.read_text(encoding="utf-8")
        ok = _step("  离乡路线Wiki 含 4 城市（盛泽到周边城市的核心路线）", "盛泽到周边城市的核心路线" in lx) and ok
        ok = _step("  离乡路线Wiki 链接到城市Wiki", "./城市Wiki.md" in lx) and ok
    else:
        ok = _step("  离乡路线Wiki 存在", False) and ok
    if XIAN_TAN.exists():
        xt = XIAN_TAN.read_text(encoding="utf-8")
        ok = _step("  闲谈素材Wiki 含 v1.7.30 城市市井特色段", "城市市井特色" in xt) and ok
        ok = _step("  闲谈素材Wiki 4 城市市井段（苏州/杭州/松江/南京）", 
                   all(c in xt for c in ["苏州阊门", "杭州清河坊", "松江棉市", "南京留都"])) and ok
    else:
        ok = _step("  闲谈素材Wiki 存在", False) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.30 4 城市集成静态验证 ===\n")
    ok1 = test_era_cities()
    ok2 = test_city_entry_events()
    ok3 = test_game_state_current_city()
    ok4 = test_agent_current_city_method()
    ok5 = test_system_base_md()
    ok6 = test_city_wiki()
    ok7 = test_other_docs_have_city_links()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]):
        print("\n🎉 7 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=}")
        sys.exit(1)
