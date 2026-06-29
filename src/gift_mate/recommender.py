from __future__ import annotations

from gift_mate.naver_search import ShopGift, search_shop

OCCASION_HINTS: dict[str, str] = {
    "생일": "생일선물",
    "100일": "100일선물",
    "취업": "취업선물",
    "집들이": "집들이선물",
    "감사": "감사선물",
    "위로": "위로선물",
    "그냥": "선물",
    "기념일": "기념일선물",
    "명절": "명절선물",
    "여행": "여행선물",
}

VIBE_HINTS: dict[str, str] = {
    "힙한": "트렌디",
    "실용": "실용",
    "감성": "감성",
    "킬러템": "인기",
    "밈맞춤": "재미",
    "MZ공감": "MZ",
}

RELATIONSHIP_HINTS: dict[str, str] = {
    "친구": "친구",
    "베프": "베스트프렌드",
    "썸": "썸",
    "연인": "연인",
    "직장동료": "직장동료",
    "선배": "선배",
    "후배": "후배",
    "부모님": "부모님",
    "형제/자매": "가족",
}


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


def _build_queries(
    *,
    relationship: str,
    occasion: str,
    vibe: str | None,
    keywords: list[str],
) -> list[tuple[str, str]]:
    occ = OCCASION_HINTS.get(occasion, occasion)
    rel = RELATIONSHIP_HINTS.get(relationship, relationship)
    vibe_word = VIBE_HINTS.get(vibe or "", vibe or "")
    extra = " ".join(keywords[:3])

    queries: list[tuple[str, str]] = []
    primary = " ".join(part for part in [occ, vibe_word, extra, rel] if part).strip()
    if primary:
        queries.append((primary, vibe or ""))

    fallback = " ".join(part for part in ["선물", vibe_word or occ, rel] if part).strip()
    if fallback and fallback != primary:
        queries.append((fallback, vibe or ""))

    if extra and extra not in primary:
        queries.append((f"선물 {extra}", vibe or ""))

    return queries or [("선물", "")]


def _score_gift(
    gift: ShopGift,
    *,
    budget_min: int,
    budget_max: int,
    vibe: str | None,
    keywords: list[str],
    occasion: str,
) -> float:
    score = 0.0

    if budget_min <= gift.price <= budget_max:
        score += 3.0
    elif gift.price > budget_max:
        over_ratio = (gift.price - budget_max) / max(budget_max, 1)
        score -= min(over_ratio * 2.0, 2.5)
    elif gift.price < budget_min:
        score -= 0.3

    title_norm = _normalize(gift.name)
    if vibe:
        vibe_norm = _normalize(vibe)
        vibe_word = _normalize(VIBE_HINTS.get(vibe, vibe))
        if vibe_norm in title_norm or vibe_word in title_norm:
            score += 2.0

    occ_hint = _normalize(OCCASION_HINTS.get(occasion, occasion))
    if occ_hint and occ_hint in title_norm:
        score += 1.0

    for kw in keywords:
        kw_norm = _normalize(kw)
        if kw_norm and kw_norm in title_norm:
            score += 0.8

    if gift.brand:
        score += 0.3

    return score


def _dedupe_gifts(gifts: list[ShopGift]) -> list[ShopGift]:
    seen: set[str] = set()
    unique: list[ShopGift] = []
    for gift in gifts:
        key = gift.product_id or _normalize(gift.name)
        if key in seen:
            continue
        seen.add(key)
        unique.append(gift)
    return unique


async def recommend_gifts(
    *,
    relationship: str,
    occasion: str,
    budget_min: int = 0,
    budget_max: int = 999_999_999,
    vibe: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[tuple[ShopGift, float]]:
    keywords = keywords or []
    queries = _build_queries(
        relationship=relationship,
        occasion=occasion,
        vibe=vibe,
        keywords=keywords,
    )

    collected: list[ShopGift] = []
    for query, vibe_hint in queries:
        try:
            results = await search_shop(query, display=20, vibe_hint=vibe_hint)
        except Exception:
            continue
        collected.extend(results)
        if len(_dedupe_gifts(collected)) >= limit * 3:
            break

    unique = _dedupe_gifts(collected)
    scored = [
        (
            gift,
            _score_gift(
                gift,
                budget_min=budget_min,
                budget_max=budget_max,
                vibe=vibe,
                keywords=keywords,
                occasion=occasion,
            ),
        )
        for gift in unique
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    in_budget = [item for item in scored if budget_min <= item[0].price <= budget_max]
    if in_budget:
        return in_budget[:limit]
    return scored[:limit]


async def find_gift_by_name(name: str) -> ShopGift | None:
    query = name.strip()
    if not query:
        return None
    results = await search_shop(query, display=5)
    name_norm = _normalize(name)
    for gift in results:
        if _normalize(gift.name) == name_norm or name_norm in _normalize(gift.name):
            return gift
    return results[0] if results else None


async def gifts_by_vibe(vibe: str, limit: int = 5) -> list[ShopGift]:
    vibe_word = VIBE_HINTS.get(vibe, vibe)
    query = f"선물 {vibe_word}".strip()
    results = await search_shop(query, display=limit * 3, vibe_hint=vibe)
    return _dedupe_gifts(results)[:limit]
