from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from gift_mate.models import Gift

DATA_PATH = Path(__file__).resolve().parent / "data" / "gifts.json"


@lru_cache(maxsize=1)
def load_gifts() -> list[Gift]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [Gift(**item) for item in raw]


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def _score_gift(
    gift: Gift,
    *,
    relationship: str,
    occasion: str,
    budget_min: int,
    budget_max: int,
    vibe: str | None,
    keywords: list[str],
) -> float:
    score = 0.0
    rel = _normalize(relationship)
    occ = _normalize(occasion)

    if any(_normalize(r) == rel or rel in _normalize(r) for r in gift.relationships):
        score += 3.0
    if any(_normalize(o) == occ or occ in _normalize(o) for o in gift.occasions):
        score += 3.0

    if gift.price_min <= budget_max and gift.price_max >= budget_min:
        score += 2.5
    elif gift.price_min > budget_max:
        score -= 1.5
    elif gift.price_max < budget_min:
        score -= 0.5

    if vibe:
        vibe_norm = _normalize(vibe)
        if any(_normalize(v) == vibe_norm or vibe_norm in _normalize(v) for v in gift.vibes):
            score += 2.0

    for kw in keywords:
        kw_norm = _normalize(kw)
        haystack = _normalize(
            " ".join(
                [
                    gift.name,
                    gift.category,
                    gift.description,
                    gift.why_mz,
                    " ".join(gift.tags),
                ]
            )
        )
        if kw_norm and kw_norm in haystack:
            score += 0.8

    return score


def recommend_gifts(
    *,
    relationship: str,
    occasion: str,
    budget_min: int = 0,
    budget_max: int = 999_999_999,
    vibe: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[tuple[Gift, float]]:
    keywords = keywords or []
    scored = [
        (gift, _score_gift(
            gift,
            relationship=relationship,
            occasion=occasion,
            budget_min=budget_min,
            budget_max=budget_max,
            vibe=vibe,
            keywords=keywords,
        ))
        for gift in load_gifts()
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [item for item in scored if item[1] > 0][:limit] or scored[:limit]


def find_gift_by_name(name: str) -> Gift | None:
    name_norm = _normalize(name)
    for gift in load_gifts():
        if _normalize(gift.name) == name_norm or name_norm in _normalize(gift.name):
            return gift
    return None


def gifts_by_vibe(vibe: str, limit: int = 5) -> list[Gift]:
    vibe_norm = _normalize(vibe)
    matched = [
        g
        for g in load_gifts()
        if any(vibe_norm in _normalize(v) or _normalize(v) == vibe_norm for v in g.vibes)
    ]
    return matched[:limit]
