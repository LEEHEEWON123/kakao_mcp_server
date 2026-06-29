from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"


@dataclass
class ShopGift:
    name: str
    price: int
    link: str
    mall_name: str
    brand: str
    category: str
    image: str = ""
    product_id: str = ""
    search_query: str = ""
    vibe_hint: str = ""

    @property
    def price_label(self) -> str:
        if self.price <= 10_000:
            return f"{self.price:,}원 (커피값)"
        if self.price <= 25_000:
            return f"{self.price:,}원 (배민한끼)"
        if self.price <= 50_000:
            return f"{self.price:,}원 (네일/헤어)"
        if self.price <= 100_000:
            return f"{self.price:,}원 (신발한켤레)"
        return f"{self.price:,}원 (flex)"

    @property
    def price_min(self) -> int:
        return self.price

    @property
    def price_max(self) -> int:
        return self.price

    @property
    def why_mz(self) -> str:
        parts = ["네이버 쇼핑 실검색"]
        if self.brand:
            parts.append(self.brand)
        if self.mall_name:
            parts.append(self.mall_name)
        return " · ".join(parts)

    @property
    def description(self) -> str:
        return self.category or "네이버 쇼핑"

    @property
    def vibes(self) -> list[str]:
        return [self.vibe_hint] if self.vibe_hint else []


def credentials_configured() -> bool:
    return bool(os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"))


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _parse_item(item: dict, *, query: str, vibe_hint: str) -> ShopGift | None:
    try:
        price = int(item.get("lprice") or 0)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    categories = [
        item.get("category1", ""),
        item.get("category2", ""),
        item.get("category3", ""),
        item.get("category4", ""),
    ]
    category = " > ".join(c for c in categories if c)

    return ShopGift(
        name=_clean_html(item.get("title", "")),
        price=price,
        link=item.get("link", ""),
        mall_name=item.get("mallName", ""),
        brand=item.get("brand", "") or item.get("maker", ""),
        category=category,
        image=item.get("image", ""),
        product_id=str(item.get("productId", "")),
        search_query=query,
        vibe_hint=vibe_hint,
    )


async def search_shop(
    query: str,
    *,
    display: int = 10,
    sort: str = "sim",
    vibe_hint: str = "",
) -> list[ShopGift]:
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ValueError(
            "NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수를 설정해주세요. "
            "https://developers.naver.com 에서 검색 API 앱을 등록하세요."
        )

    params = {
        "query": query.strip(),
        "display": min(max(display, 1), 100),
        "sort": sort,
    }
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(NAVER_SHOP_URL, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])

    results: list[ShopGift] = []
    for item in items:
        parsed = _parse_item(item, query=query, vibe_hint=vibe_hint)
        if parsed:
            results.append(parsed)
    return results
