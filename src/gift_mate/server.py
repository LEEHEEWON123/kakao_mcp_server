from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from gift_mate.messages import draft_message, format_gift_card
from gift_mate.models import BUDGET_LABELS
from gift_mate.naver_search import ShopGift, credentials_configured
from gift_mate.recommender import find_gift_by_name, gifts_by_vibe, recommend_gifts

INSTRUCTIONS = """
너는 MZ 감성 선물 큐레이터 '기프트메이트(Gift Mate)'야.
네이버 쇼핑 실검색으로 관계·상황·예산·취향(vibe)에 맞는 선물을 추천해.
추천 결과에는 실제 상품명·가격·구매 링크가 포함돼.
추천 후 카카오톡/인스타 DM용 메시지 초안도 같이 제안해줘.
말투는 친근하고 공감 가는 MZ 톤. 과장되거나 억지 슬랭은 피해.
""".strip()

mcp = FastMCP(
    name="기프트메이트 — 선물 고민 종결",
    instructions=INSTRUCTIONS,
    host="0.0.0.0",
    streamable_http_path="/mcp",
    stateless_http=True,
)


def _parse_budget(budget: str) -> tuple[int, int]:
    label = budget.strip()
    if label in BUDGET_LABELS:
        return BUDGET_LABELS[label]
    if "~" in label and "만" in label:
        parts = label.replace("원", "").replace("만", "").split("~")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 10_000, int(parts[1]) * 10_000
            except ValueError:
                pass
    return 0, 999_999_999


def _format_gift(gift: ShopGift, rank: int) -> str:
    return format_gift_card(
        gift.name,
        gift.price_label,
        gift.why_mz,
        rank,
        link=gift.link,
        mall_name=gift.mall_name,
    )


def _api_error_message(exc: Exception) -> str:
    msg = str(exc)
    if "NAVER_CLIENT" in msg:
        return (
            "⚠️ 네이버 API 키가 설정되지 않았어.\n"
            "서버에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수를 등록해줘.\n"
            "발급: https://developers.naver.com/apps/#/register (검색 API 선택)"
        )
    return f"⚠️ 네이버 쇼핑 검색 실패: {msg}"


@mcp.tool(
    name="recommend_gift",
    description=(
        "네이버 쇼핑 실검색으로 관계·상황·예산·취향에 맞는 선물 TOP 3~5 추천. "
        "예: '베프 생일, 3만원대, 감성적인 거'. "
        "budget: 커피값|배민한끼|네일/헤어|신발한켤레|flex 또는 '3~5만원'"
    ),
)
async def recommend_gift(
    relationship: str,
    occasion: str,
    budget: str = "배민한끼",
    vibe: str = "",
    extra_context: str = "",
    count: int = 3,
) -> str:
    """선물 추천 메인 도구 — 네이버 쇼핑 실검색."""
    if not credentials_configured():
        return _api_error_message(ValueError("NAVER_CLIENT"))

    budget_min, budget_max = _parse_budget(budget)
    keywords = [w for w in extra_context.replace(",", " ").split() if w.strip()]
    if vibe.strip():
        keywords.append(vibe.strip())

    try:
        results = await recommend_gifts(
            relationship=relationship,
            occasion=occasion,
            budget_min=budget_min,
            budget_max=budget_max,
            vibe=vibe.strip() or None,
            keywords=keywords,
            limit=min(max(count, 1), 5),
        )
    except Exception as exc:
        return _api_error_message(exc)

    if not results:
        return (
            "🤔 딱 맞는 선물을 못 찾았어.\n"
            "예산 범위를 넓히거나 vibe(힙한/실용/감성/밈맞춤)를 바꿔서 다시 물어봐!"
        )

    header = (
        f"🎁 **{relationship}**에게 **{occasion}** 선물 추천 (네이버 쇼핑 실검색)\n"
        f"💰 예산: {budget} | ✨ vibe: {vibe or '자동'}\n"
        "—" * 20
    )
    lines = [header, ""]
    for i, (gift, _score) in enumerate(results, start=1):
        lines.append(_format_gift(gift, i))
        lines.append(f"   💬 {gift.description}")
        lines.append("")

    lines.append("💡 **Tip**: `draft_gift_message`로 카톡 메시지 초안도 만들어줄게!")
    return "\n".join(lines)


@mcp.tool(
    name="draft_gift_message",
    description=(
        "선택한 선물에 맞는 카카오톡/인스타 DM 메시지 초안 작성. "
        "tone: casual(친근) | funny(웃김) | heartfelt(진심) | formal(격식) | mz_slang(MZ슬랭)"
    ),
)
async def draft_gift_message(
    recipient_name: str,
    gift_name: str,
    tone: Literal["casual", "funny", "heartfelt", "formal", "mz_slang"] = "casual",
    occasion: str = "그냥",
) -> str:
    """선물 메시지 초안."""
    message = draft_message(
        recipient_name=recipient_name,
        gift_name=gift_name,
        tone=tone,
        occasion=occasion,
    )
    tip = ""
    if credentials_configured():
        try:
            gift = await find_gift_by_name(gift_name)
            if gift:
                tip = f"\n\n📎 참고: {gift.price_label} · {gift.link}"
        except Exception:
            pass
    return f"📱 **메시지 초안** ({tone})\n\n{message}{tip}"


@mcp.tool(
    name="compare_gifts",
    description="두 가지 선물 후보 A vs B 비교 — 네이버 쇼핑 실검색 기준 가격·쇼핑몰·추천",
)
async def compare_gifts(gift_a: str, gift_b: str, relationship: str = "친구") -> str:
    """선물 A/B 비교."""
    if not credentials_configured():
        return _api_error_message(ValueError("NAVER_CLIENT"))

    try:
        a, b = await find_gift_by_name(gift_a), await find_gift_by_name(gift_b)
    except Exception as exc:
        return _api_error_message(exc)

    if not a and not b:
        return f"⚠️ '{gift_a}', '{gift_b}' 둘 다 검색 결과가 없어. 다른 키워드로 다시 시도해봐!"

    lines = [f"⚖️ **{relationship}**에게 줄 선물, 뭐가 나을까? (네이버 쇼핑)", ""]

    for label, gift, query in [("A", a, gift_a), ("B", b, gift_b)]:
        if gift:
            lines.append(f"**[{label}] {gift.name}** ({gift.price_label})")
            lines.append(f"  ✅ {gift.description}")
            lines.append(f"  🏪 {gift.mall_name}")
            lines.append(f"  🔗 {gift.link}")
        else:
            lines.append(f"**[{label}] {query}** — 검색 결과 없음")
        lines.append("")

    if a and b:
        if a.price < b.price:
            verdict = f"예산 아끼려면 **{a.name}** ({a.price:,}원), flex 하려면 **{b.name}** ({b.price:,}원)"
        elif b.price < a.price:
            verdict = f"예산 아끼려면 **{b.name}** ({b.price:,}원), flex 하려면 **{a.name}** ({a.price:,}원)"
        else:
            verdict = f"가격 비슷! **{relationship}** 취향에 맞는 쪽으로 — {a.mall_name} vs {b.mall_name}"
        lines.append(f"🏆 **한줄 결론**: {verdict}")

    return "\n".join(lines)


@mcp.tool(
    name="gift_by_vibe",
    description="vibe만으로 네이버 쇼핑 실검색 선물 추천. vibe: 힙한|실용|감성|킬러템|밈맞춤|MZ공감",
)
async def gift_by_vibe(vibe: str, count: int = 5) -> str:
    """vibe 기반 빠른 추천."""
    if not credentials_configured():
        return _api_error_message(ValueError("NAVER_CLIENT"))

    try:
        matched = await gifts_by_vibe(vibe, limit=min(max(count, 1), 5))
    except Exception as exc:
        return _api_error_message(exc)

    if not matched:
        return f"🤷 '{vibe}' vibe에 맞는 선물이 없어. 힙한/실용/감성/킬러템/밈맞춤/MZ공감 중 골라봐!"

    lines = [f"✨ **{vibe}** vibe 선물 리스트 (네이버 쇼핑 실검색)", ""]
    for i, gift in enumerate(matched, start=1):
        lines.append(_format_gift(gift, i))
    return "\n".join(lines)


mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(app):
        yield


app = FastAPI(
    title="Gift Mate MCP",
    description="MZ 감성 선물 고민 종결 MCP — PlayMCP (네이버 쇼핑 실검색)",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "gift-mate-mcp",
        "naver_api": credentials_configured(),
    }


for route in mcp_app.routes:
    app.router.routes.append(route)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "gift_mate.server:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )


if __name__ == "__main__":
    main()
