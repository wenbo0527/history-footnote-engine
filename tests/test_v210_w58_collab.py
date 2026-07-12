"""🆕 v2.10.x W58: 协作测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W58_001_create_and_join():
    from history_footnote.collab import collab_create, collab_join
    cid = collab_create("sess-1", max_users=3)
    assert collab_join(cid, "user-a")
    assert collab_join(cid, "user-b")


def test_W58_002_max_users():
    from history_footnote.collab import collab_create, collab_join
    cid = collab_create("sess-2", max_users=2)
    collab_join(cid, "u1")
    collab_join(cid, "u2")
    assert not collab_join(cid, "u3")


def test_W58_003_action():
    from history_footnote.collab import collab_create, collab_join, collab_action
    cid = collab_create("sess-3")
    collab_join(cid, "u1")
    s = collab_action(cid, "u1", "hi")
    assert s["round"] == 1
    assert "hi" in s["narrative"]


def test_W58_004_state_users():
    from history_footnote.collab import collab_create, collab_join, collab_state
    cid = collab_create("sess-4")
    collab_join(cid, "u1")
    collab_join(cid, "u2")
    s = collab_state(cid)
    assert len(s["users"]) == 2


def test_W58_005_nonexistent():
    from history_footnote.collab import collab_join
    assert not collab_join("nonexistent", "u1")


def test_W58_006_leave():
    from history_footnote.collab import collab_create, collab_join, collab_leave
    cid = collab_create("sess-5")
    collab_join(cid, "u1")
    assert collab_leave(cid, "u1")
    assert not collab_leave(cid, "u1")
