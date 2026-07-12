"""🆕 v2.10.x W64: Stripe 测试"""
import sys
import hashlib, hmac
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W64_001_customer():
    from history_footnote.integrations import stripe_create_customer
    r = stripe_create_customer("a@b.com")
    assert r["ok"]
    assert r["customer_id"].startswith("cus_")


def test_W64_002_invalid_email():
    from history_footnote.integrations import stripe_create_customer
    assert not stripe_create_customer("invalid")["ok"]


def test_W64_003_subscription():
    from history_footnote.integrations import stripe_create_subscription
    r = stripe_create_subscription("cus_1", "pro_monthly")
    assert r["ok"]
    assert r["status"] == "active"


def test_W64_004_unknown_price():
    from history_footnote.integrations import stripe_create_subscription
    assert not stripe_create_subscription("cus_1", "fake")["ok"]


def test_W64_005_webhook():
    from history_footnote.integrations import stripe_webhook_verify
    payload = '{"e": 1}'
    secret = "whsec_x"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    assert stripe_webhook_verify(payload, sig, secret)["verified"]


def test_W64_006_invalid_webhook():
    from history_footnote.integrations import stripe_webhook_verify
    assert not stripe_webhook_verify("x", "wrong", "s")["verified"]
