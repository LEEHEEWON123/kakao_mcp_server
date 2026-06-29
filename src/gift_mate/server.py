from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from gift_mate.messages import draft_message, format_gift_card
from gift_mate.models import BUDGET_LABELS
from gift_mate.recommender import find_gift_by_name, gifts_by_vibe, recommend_gifts

INSTRUCTIONS = """
너는 MZ 감성 선물 큐레이터 '기프트메이트(Gift Mate)'야.
사용자가 "뭐 사줄까?" 고민할 때 관계·상황·예산·취향(vibe)에 맞는 선물을 추천해.
추천 후 카카오톡/인스타 DM용 메시지 초안도 같이 제안해줘.
말투는 친근하고 공감 가는 MZ 톤. 과장되거나 억지 슬랭은 피해.
""".strip()

mcp = FastMCP(
    name="기프트메이트 — 선물 고민 종결",
    instructions=INSTRUCTIONS,
    host="0.0.0.0",
    streamable_http_path="/",
    stateless_http=True,
)


def _parse_budget(budget: str) -> tuple[int, int]:
    label = budget.strip()
    if label in BUDGET_LABELS:
        return BUDGET_LABELS[label]
    if "~" in label and "만" in label:
        # e.g. "3~5만원"
        parts = label.replace("원", "").replace("만", "").split("~")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 10_000, int(parts[1]) * 10_000
            except ValueError:
                pass
    return 0, 999_999_999


@mcp.tool(
    name="recommend_gift",
    description=(
        "관계·상황·예산·취향에 맞는 MZ 감성 선물 TOP 3~5 추천. "
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
    """선물 추천 메인 도구."""
    budget_min, budget_max = _parse_budget(budget)
    keywords = [w for w in extra_context.replace(",", " ").split() if w.strip()]
    if vibe.strip():
        keywords.append(vibe.strip())

    results = recommend_gifts(
        relationship=relationship,
        occasion=occasion,
        budget_min=budget_min,
        budget_max=budget_max,
        vibe=vibe.strip() or None,
        keywords=keywords,
        limit=min(max(count, 1), 5),
    )

    if not results:
        return (
            "🤔 딱 맞는 선물을 못 찾았어.\n"
            "예산 범위를 넓히거나 vibe(힙한/실용/감성/밈맞춤)를 바꿔서 다시 물어봐!"
        )

    header = (
        f"🎁 **{relationship}**에게 **{occasion}** 선물 추천\n"
        f"💰 예산: {budget} | ✨ vibe: {vibe or '자동'}\n"
        "—" * 20
    )
    lines = [header, ""]
    for i, (gift, _score) in enumerate(results, start=1):
        lines.append(format_gift_card(gift.name, gift.price_label, gift.why_mz, i))
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
    gift = find_gift_by_name(gift_name)
    tip = ""
    if gift:
        tip = f"\n\n📎 참고: {gift.why_mz}"
    return f"📱 **메시지 초안** ({tone})\n\n{message}{tip}"


@mcp.tool(
    name="compare_gifts",
    description="두 가지 선물 후보 A vs B 비교 — MZ 관점에서 장단점·추천 대상 정리",
)
async def compare_gifts(gift_a: str, gift_b: str, relationship: str = "친구") -> str:
    """선물 A/B 비교."""
    a = find_gift_by_name(gift_a)
    b = find_gift_by_name(gift_b)

    if not a and not b:
        return f"⚠️ '{gift_a}', '{gift_b}' 둘 다 DB에 없어. `recommend_gift`로 후보를 먼저 받아봐!"

    lines = [f"⚖️ **{relationship}**에게 줄 선물, 뭐가 나을까?", ""]

    for label, gift in [("A", a), ("B", b)]:
        if gift:
            lines.append(f"**[{label}] {gift.name}** ({gift.price_label})")
            lines.append(f"  ✅ 장점: {gift.description}")
            lines.append(f"  🔥 MZ포인트: {gift.why_mz}")
            lines.append(f"  🏷 vibe: {', '.join(gift.vibes)}")
        else:
            lines.append(f"**[{label}]** DB에 없음 — 직접 입력한 선물로 비교")
        lines.append("")

    if a and b:
        if a.price_max < b.price_min:
            verdict = f"예산 아끼려면 **{a.name}**, flex 하려면 **{b.name}**"
        elif b.price_max < a.price_min:
            verdict = f"예산 아끼려면 **{b.name}**, flex 하려면 **{a.name}**"
        else:
            verdict = f"**{relationship}**한테는 vibe '{', '.join(a.vibes)}' vs '{', '.join(b.vibes)}' 중 취향 맞추기!"
        lines.append(f"🏆 **한줄 결론**: {verdict}")

    return "\n".join(lines)


@mcp.tool(
    name="gift_by_vibe",
    description="vibe만으로 빠른 선물 추천. vibe: 힙한|실용|감성|킬러템|밈맞춤|MZ공감",
)
async def gift_by_vibe(vibe: str, count: int = 5) -> str:
    """vibe 기반 빠른 추천."""
    matched = gifts_by_vibe(vibe, limit=min(max(count, 1), 5))
    if not matched:
        return f"🤷 '{vibe}' vibe에 맞는 선물이 없어. 힙한/실용/감성/킬러템/밈맞춤/MZ공감 중 골라봐!"

    lines = [f"✨ **{vibe}** vibe 선물 리스트", ""]
    for i, gift in enumerate(matched, start=1):
        lines.append(format_gift_card(gift.name, gift.price_label, gift.why_mz, i))
    return "\n".join(lines)


mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(app):
        yield


app = FastAPI(
    title="Gift Mate MCP",
    description="MZ 감성 선물 고민 종결 MCP — PlayMCP",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gift-mate-mcp"}


app.mount("/mcp", mcp_app)


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
