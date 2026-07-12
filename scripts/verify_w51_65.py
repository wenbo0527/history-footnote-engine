"""Verify v2.10.x W57-W65 modules (inline exec, no importlib)."""
import sys
import time
import types
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def load(name):
    path = SRC / "history_footnote" / f"{name}.py"
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    exec(code, mod.__dict__)
    return mod


mods = {}
t = time.time()
print("loading start", flush=True)
for n in ["i18n_prompts", "collab", "replay", "ai_image", "era_validator", "api_gateway", "integrations", "analytics"]:
    print(f"  before load {n}", flush=True)
    mods[n] = load(n)
    print(f"  {n}: loaded", flush=True)
print(f"  total load: {round(time.time()-t, 2)}s", flush=True)


def t_W57():
    f = mods["i18n_prompts"].get_chapter_blueprint_prompt
    p = f("zh-CN", chapter=1, total_chapters=10, era_id="wanli1587", identity="weaving_male")
    assert "第 1 章" in p
    p = f("en-US", chapter=3, total_chapters=5, era_id="hongwu1399", identity="scholar")
    assert "Chapter 3" in p


def t_W58():
    m = mods["collab"]
    cid = m.collab_create("s1", max_users=3)
    assert m.collab_join(cid, "u1")
    assert m.collab_join(cid, "u2")
    s = m.collab_action(cid, "u1", "hi")
    assert s["round"] == 1
    assert "hi" in s["narrative"]
    assert not m.collab_join("nonexistent", "u1")
    assert m.collab_leave(cid, "u1")


def t_W59():
    m = mods["replay"]
    m.replay_record_chapter("s1", 1, "narration", [{"choice": "a"}], "summary", 100.0, 200.0)
    r = m.replay_chapter("s1", 1)
    assert r["narrative"] == "narration"
    meta = m.replay_chapter_meta("s1", 1)
    assert meta["duration_seconds"] == 100.0
    assert m.replay_list_chapters("s1") == [1]
    assert m.replay_delete_chapter("s1", 1)


def t_W60():
    m = mods["ai_image"]
    img = m.ai_image_generate("test", "style")
    assert img["url"].endswith(".webp")
    imgs = m.ai_image_bulk(["a", "b"])
    assert len(imgs) == 2
    assert imgs[0]["url"] != imgs[1]["url"]
    prompts = m.extract_image_prompts("夜深。月光如水。周文衡抚琴。" * 5, max_count=3)
    assert len(prompts) <= 3


def t_W61():
    m = mods["era_validator"]
    era = {
        "era_id": "x", "title": "t", "year": 1,
        "narrative": {"setting": "a", "tone": "b", "main_conflict": "c"},
        "characters": [{"id": "c1", "name": "A"}],
        "fate_cards": [{"id": "f1"}],
    }
    assert m.era_validate(era)["valid"]
    assert not m.era_validate({"era_id": "x"})["valid"]
    f = m.era_required_fields()
    assert "era_id" in f
    assert m.era_fix({"era_id": "x"}).get("narrative") is not None


def t_W62():
    m = mods["api_gateway"]
    m.rate_limit_reset("u1")
    assert m.rate_limit_check("u1", limit=5)["allowed"]
    spec = m.openapi_spec()
    assert spec["openapi"] == "3.0.0"
    assert "/api/input" in spec["paths"]
    assert m.api_key_validate("demo_key") is not None
    k = m.api_key_register("test", "pro")
    assert m.api_key_validate(k) is not None


def t_W63():
    m = mods["integrations"]
    assert len(m.discord_format_narrative("a" * 3000)) <= 2000
    r = m.discord_send_message("c1", "hi", "tok")
    assert r["sent"]
    e = m.discord_embed_narrative("T", "n", 5)
    assert e["embeds"][0]["title"] == "T"


def t_W64():
    m = mods["integrations"]
    r = m.stripe_create_customer("a@b.com")
    assert r["ok"]
    r = m.stripe_create_subscription("cus_1", "pro_monthly")
    assert r["ok"]
    r = m.stripe_create_subscription("cus_1", "fake_tier")
    assert not r["ok"]


def t_W65():
    m = mods["analytics"]
    m.analytics_clear()
    m.analytics_track_event("session_created", {"era_id": "wanli1587"})
    m.analytics_track_event("llm_call", {"prompt_tokens": 100, "completion_tokens": 50})
    s = m.analytics_summary()
    assert s["sessions_created"] == 1
    assert s["total_llm_tokens"] == 150
    by = m.analytics_by_era()
    assert by["wanli1587"]["sessions"] == 1


tests = [
    ("W57 i18n_prompts", t_W57),
    ("W58 collab", t_W58),
    ("W59 replay", t_W59),
    ("W60 ai_image", t_W60),
    ("W61 era_validator", t_W61),
    ("W62 api_gateway", t_W62),
    ("W63 discord", t_W63),
    ("W64 stripe", t_W64),
    ("W65 analytics", t_W65),
]
passed = failed = 0
for name, fn in tests:
    print(f"  starting {name}...", flush=True)
    try:
        fn()
        print(f"  {name}: PASS", flush=True)
        passed += 1
    except Exception as e:
        print(f"  {name}: FAIL -- {e}", flush=True)
        failed += 1
print(f"\n  {passed}/{passed+failed} sprint modules verified", flush=True)
sys.exit(0 if failed == 0 else 1)
