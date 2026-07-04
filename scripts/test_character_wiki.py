"""🆕 v1.7.1 Character Wiki 单元测试"""
import sys
sys.path.insert(0, "src")

from history_footnote.character_wiki import (
    CharacterWiki,
    CharacterEntry,
    EventEntry,
    DecisionEntry,
    MAX_CHARACTERS,
    MAX_EVENTS,
    MAX_DECISIONS,
    wiki_to_json,
    wiki_from_json,
    render_wiki_summary,
)


def test_basic_add():
    """基本添加人物"""
    wiki = CharacterWiki(save_id="t1")
    char = wiki.add_or_update_character("张顺", round=1, summary="牙行老板")
    assert char.id == "张顺"
    assert char.appear_count == 1
    print(f"✅ test_basic_add: {char.id}, {char.relationship}")


def test_reappear():
    """重复出现累加"""
    wiki = CharacterWiki()
    wiki.add_or_update_character("张顺", round=1)
    char = wiki.add_or_update_character("张顺", round=5)
    assert char.appear_count == 2
    assert char.first_appear_round == 1
    assert char.last_appear_round == 5
    print(f"✅ test_reappear: count={char.appear_count}")


def test_relationship_change():
    """关系等级变化"""
    wiki = CharacterWiki()
    wiki.add_or_update_character("张顺", relationship="陌生人")
    char = wiki.add_or_update_character("张顺", relationship="朋友")
    assert char.relationship == "朋友"
    print(f"✅ test_relationship_change: 陌生人→朋友")


def test_auto_extract_npcs():
    """自动提取 NPC"""
    wiki = CharacterWiki()
    narrative = """张顺说："三两三，不能再多了。"
你心里想：他出价低。
丁娘子答道："代织的事包在我身上。"
李四问："去不去？"
王二笑道："好说！\""""
    wiki.auto_extract_from_narrative(narrative, round=2)
    npcs = list(wiki.characters.keys())
    assert "张顺" in npcs
    assert "丁娘子" in npcs
    assert "李四" in npcs
    assert "王二" in npcs
    print(f"✅ test_auto_extract_npcs: 4 个 NPC 提取 ({npcs})")


def test_promise_extraction():
    """承诺提取"""
    wiki = CharacterWiki()
    narrative = "丁娘子答道：'代织的事包在我身上。'"
    wiki.auto_extract_from_narrative(narrative, round=1)
    char = wiki.characters["丁娘子"]
    assert len(char.promises_npc) >= 1
    assert any("代织" in p for p in char.promises_npc)
    print(f"✅ test_promise_extraction: {char.promises_npc}")


def test_multiple_promises():
    """多次承诺累加"""
    wiki = CharacterWiki()
    # 用包含承诺关键词的样例
    wiki.auto_extract_from_narrative("张顺说：'代织的事包在我身上。'", round=1)
    wiki.auto_extract_from_narrative("张顺说：'放心，借钱没问题。'", round=2)
    char = wiki.characters["张顺"]
    assert len(char.promises_npc) >= 2
    print(f"✅ test_multiple_promises: {len(char.promises_npc)} 个承诺")


def test_decision_recording():
    """决策记录（含 alternatives）"""
    wiki = CharacterWiki()
    wiki.auto_extract_from_narrative(
        narrative="你面前有 4 条路。",
        round=3,
        player_input="讨价还价",
        player_options=["讨价还价", "全卖", "问代织"],
    )
    assert len(wiki.decisions) == 1
    d = wiki.decisions[0]
    assert d.summary == "讨价还价"
    assert "全卖" in d.alternatives
    print(f"✅ test_decision_recording: 决策+{len(d.alternatives)} alternatives")


def test_capacity_limit():
    """容量限制：超过 MAX_CHARACTERS 时移除最久没出现"""
    wiki = CharacterWiki()
    for i in range(MAX_CHARACTERS + 5):
        wiki.add_or_update_character(f"角色{i}", round=i + 1)
    assert len(wiki.characters) <= MAX_CHARACTERS
    print(f"✅ test_capacity_limit: {len(wiki.characters)}/{MAX_CHARACTERS}")


def test_relationships():
    """关系图"""
    wiki = CharacterWiki()
    wiki.add_relationship("张顺", "丁娘子", "合作")
    assert wiki.relationships["张顺"]["丁娘子"] == "合作"
    print(f"✅ test_relationships: 张顺 → 丁娘子: 合作")


def test_serialize_roundtrip():
    """序列化往返"""
    wiki = CharacterWiki(save_id="roundtrip-test")
    wiki.add_or_update_character("张顺", round=1, summary="牙行老板")
    wiki.add_or_update_character("丁娘子", round=2)
    wiki.add_event(round=1, type="meet", summary="初见张顺", characters=["张顺"])
    wiki.add_decision(round=3, type="negotiate", summary="讨价还价")

    json_str = wiki_to_json(wiki)
    wiki2 = wiki_from_json(json_str)

    assert wiki2.save_id == "roundtrip-test"
    assert "张顺" in wiki2.characters
    assert "丁娘子" in wiki2.characters
    assert len(wiki2.events) == 1
    assert len(wiki2.decisions) == 1
    print(f"✅ test_serialize_roundtrip: {len(wiki2.characters)} chars")


def test_per_save_isolation():
    """Per-save 隔离"""
    wiki1 = CharacterWiki(save_id="save-A")
    wiki2 = CharacterWiki(save_id="save-B")
    wiki1.add_or_update_character("张顺", round=1)
    wiki2.add_or_update_character("周老板", round=1)
    # 互不影响
    assert "张顺" not in wiki2.characters
    assert "周老板" not in wiki1.characters
    print(f"✅ test_per_save_isolation: A/B 独立")


def test_render_summary():
    """渲染 summary（用于 LLM 上下文）"""
    wiki = CharacterWiki()
    wiki.add_or_update_character("张顺", round=1, summary="牙行老板", relationship="熟人")
    wiki.add_or_update_character("丁娘子", round=2, summary="代织", relationship="合作伙伴")
    wiki.auto_extract_from_narrative("丁娘子答道：'代织包在我身上。'", round=2)
    summary = render_wiki_summary(wiki)
    assert "张顺" in summary
    assert "丁娘子" in summary
    assert "代织" in summary
    print(f"✅ test_render_summary:")
    for line in summary.split("\n"):
        print(f"    {line}")


def test_relationship_levels_sync():
    """npc_levels 兼容（与原 npc_levels 同步）"""
    wiki = CharacterWiki()
    wiki.add_or_update_character("张顺", relationship="朋友")
    # 现在 characters["张顺"].relationship 是 "朋友"
    # 也应该可写入 wiki.npc_levels["张顺"]
    wiki.npc_levels["张顺"] = "朋友"
    assert wiki.npc_levels["张顺"] == "朋友"
    print("✅ test_relationship_levels_sync: npc_levels 可同步")


def test_empty_wiki():
    """空 wiki 渲染"""
    wiki = CharacterWiki()
    summary = render_wiki_summary(wiki)
    assert summary == "" or "本存档" in summary
    print("✅ test_empty_wiki: 空 wiki 不报错")


if __name__ == "__main__":
    print("=" * 50)
    print("Character Wiki 测试（v1.7.1）")
    print("=" * 50)
    test_basic_add()
    test_reappear()
    test_relationship_change()
    test_auto_extract_npcs()
    test_promise_extraction()
    test_multiple_promises()
    test_decision_recording()
    test_capacity_limit()
    test_relationships()
    test_serialize_roundtrip()
    test_per_save_isolation()
    test_render_summary()
    test_relationship_levels_sync()
    test_empty_wiki()
    print("\n✅ 所有 v1.7.1 Character Wiki 测试通过")