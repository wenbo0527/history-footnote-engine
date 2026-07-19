"""🆕 v2.10.x W63-W64: Discord + Stripe 集成

Discord Bot:
- discord_send_message(channel_id, content) → {sent: bool, message_id}
- discord_format_narrative(text) → discord-formatted (max 2000 chars, embed)

Stripe:
- stripe_create_customer(email) → {customer_id}
- stripe_create_subscription(customer_id, price_id) → {subscription_id, status}
- stripe_webhook_verify(payload, signature) → {verified: bool, event}
"""
from __future__ import annotations
import hashlib
import hmac
import time
import re
from typing import Literal


# ============================================================
# Discord (W63)
# ============================================================

def discord_format_narrative(text: str, max_length: int = 2000) -> str:
    """格式化叙事为 Discord 友好格式

    - max 2000 字符（Discord 单消息上限）
    - 自动截断
    - 加 footer marker
    """
    if not text:
        return ""
    if len(text) <= max_length - 50:  # 预留 footer
        return text + "\n\n_— 来自《史脚注》DM_"
    # 截断
    truncated = text[:max_length - 80] + "..."
    return truncated + "\n\n_(已截断)_ _— 来自《史脚注》DM_"


def discord_send_message(
    channel_id: str,
    content: str,
    bot_token: str = "",
) -> dict:
    """发送 Discord 消息（mock）

    真实环境应调 Discord API:
    POST https://discord.com/api/v10/channels/{channel_id}/messages
    Authorization: Bot {bot_token}
    """
    if not channel_id:
        return {"sent": False, "error": "channel_id required"}
    if not content:
        return {"sent": False, "error": "content required"}
    if not bot_token:
        return {"sent": False, "error": "bot_token required"}

    # 截断过长的消息
    content = discord_format_narrative(content)

    # mock
    message_id = hashlib.md5(f"{channel_id}_{content}_{time.time()}".encode()).hexdigest()[:18]
    return {
        "sent": True,
        "channel_id": channel_id,
        "message_id": message_id,
        "content_length": len(content),
    }


def discord_embed_narrative(
    title: str,
    narrative: str,
    chapter: int = 0,
    color: int = 0x8F4B28,  # bronze
) -> dict:
    """生成 Discord embed 对象"""
    return {
        "embeds": [
            {
                "title": title,
                "description": narrative[:2048],
                "color": color,
                "footer": {"text": f"第 {chapter} 章 · 《史脚注》" if chapter else "《史脚注》"},
            },
        ],
    }


# ============================================================
# Stripe (W64)
# ============================================================

PRICE_TIERS = {
    "free": {"amount": 0, "interval": "month", "name": "Free"},
    "pro_monthly": {"amount": 2999, "interval": "month", "name": "Pro Monthly"},  # $29.99
    "pro_yearly": {"amount": 29999, "interval": "year", "name": "Pro Yearly"},  # $299.99
    "enterprise": {"amount": 99999, "interval": "month", "name": "Enterprise"},
}


def stripe_create_customer(email: str) -> dict:
    """创建 Stripe 客户（mock）"""
    if not email or "@" not in email:
        return {"ok": False, "error": "invalid email"}
    customer_id = "cus_" + hashlib.md5(email.encode()).hexdigest()[:14]
    return {"ok": True, "customer_id": customer_id, "email": email}


def stripe_create_subscription(
    customer_id: str,
    price_id: str,
) -> dict:
    """创建订阅"""
    if not customer_id or not price_id:
        return {"ok": False, "error": "missing params"}
    tier = PRICE_TIERS.get(price_id)
    if not tier:
        return {"ok": False, "error": f"unknown price_id: {price_id}"}
    sub_id = "sub_" + hashlib.md5(f"{customer_id}_{price_id}_{time.time()}".encode()).hexdigest()[:14]
    return {
        "ok": True,
        "subscription_id": sub_id,
        "customer_id": customer_id,
        "price_id": price_id,
        "tier": price_id,
        "amount": tier["amount"],
        "interval": tier["interval"],
        "status": "active",
    }


def stripe_webhook_verify(
    payload: str,
    signature: str,
    secret: str = "whsec_test",
) -> dict:
    """验证 Stripe webhook 签名（mock）"""
    if not payload or not signature:
        return {"verified": False, "error": "missing params"}
    # 计算 HMAC-SHA256
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    if hmac.compare_digest(expected, signature):
        return {"verified": True}
    return {"verified": False, "error": "invalid signature"}


def stripe_list_prices() -> list[dict]:
    """列出所有价格档"""
    return [{"id": k, **v} for k, v in PRICE_TIERS.items()]
