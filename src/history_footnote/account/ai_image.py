"""🆕 v2.10.x W60: AI 自动配图（章节叙事 + 场景图）

根据章节叙事 prompt 生成场景图 URL
- ai_image_generate(prompt, style="国风水墨") → {url, prompt, style, seed}
- ai_image_bulk(prompts) → [image]
"""
from __future__ import annotations
import hashlib
import time
import re
from typing import Literal

# 简化版：根据 prompt hash 生成 stable URL
# 真实环境应调 image API（minimax image-01 / openai dall-e / etc.）

def _hash_prompt(prompt: str) -> str:
    return hashlib.md5(prompt.encode("utf-8")).hexdigest()[:12]


def _slugify(prompt: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", prompt)[:32]
    return s or "image"


def ai_image_generate(
    prompt: str,
    style: str = "国风水墨",
    size: str = "1024x1024",
) -> dict:
    """生成图片 URL（基于 prompt hash 的 stable URL）

    真实实现应调 image API；这里生成占位 URL。
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt cannot be empty")
    seed = _hash_prompt(prompt + style)
    slug = _slugify(prompt)
    return {
        "url": f"/static/ai_images/{seed}_{slug}.webp",
        "prompt": prompt,
        "style": style,
        "size": size,
        "seed": seed,
        "generated_at": time.time(),
    }


def ai_image_bulk(prompts: list[str], style: str = "国风水墨") -> list[dict]:
    """批量生成"""
    return [ai_image_generate(p, style) for p in prompts if p.strip()]


def extract_image_prompts(narrative: str, max_count: int = 3) -> list[str]:
    """从叙事中提取适合配图的句子

    简化版：取前 N 个 30-100 字的句子
    """
    if not narrative:
        return []
    sentences = re.split(r"[。！？\.\!\?]", narrative)
    candidates = [
        s.strip() for s in sentences
        if 30 <= len(s.strip()) <= 100
    ]
    return candidates[:max_count]
