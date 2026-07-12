"""🆕 v2.10.x W63: Discord 测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W63_001_truncate():
    from history_footnote.integrations import discord_format_narrative
    assert len(discord_format_narrative("a" * 3000)) <= 2000


def test_W63_002_send():
    from history_footnote.integrations import discord_send_message
    r = discord_send_message("c1", "hi", "tok")
    assert r["sent"]


def test_W63_003_missing():
    from history_footnote.integrations import discord_send_message
    assert not discord_send_message("", "x", "t")["sent"]


def test_W63_004_embed():
    from history_footnote.integrations import discord_embed_narrative
    e = discord_embed_narrative("T", "n", 5)
    assert e["embeds"][0]["title"] == "T"
