from __future__ import annotations

from gift_mate.models import MessageTone

TEMPLATES: dict[MessageTone, list[str]] = {
    "casual": [
        "{name}아 생일 축하해! 🎂\n{gift} 샀는데 네 취향일 것 같아서 ㅎㅎ\n마음에 들면 좋겠다!",
        "야 {name}!! {gift} 보냄 ㅋㅋ\n센스 좀 봐라~ 잘 써!",
        "{name}~ {gift} 작지만 진심이야 ✨\n고마워 항상!",
    ],
    "funny": [
        "{name} 생일 축하 🎉\n{gift} 받아라 ㅋㅋㅋ\n거절하면 서운해함 (진심)",
        "선물 도착 🎁\n내가 {gift} 골라줬거든?\n감동해서 울지 마 ㅋㅋ",
        "{name}야 이거 {gift}인데\nMZ 선물 레벨업했다고 ㅋㅋ\n인증샷 ㄱㄱ",
    ],
    "heartfelt": [
        "{name}아, 항상 고마워.\n{gift} 작은 선물이지만\n네가 좋아했으면 해 💛",
        "요즘 바쁘지? {gift} 보냈어.\n잠깐이라도 쉬면서 써줘.\n항상 응원해!",
        "{name} 생일 진심으로 축하해 🎂\n{gift} — 네 취향 생각하면서 골랐어.\n오래오래 좋은 일만!",
    ],
    "formal": [
        "{name}님, {occasion} 진심으로 축하드립니다.\n{gift} 보내드렸습니다. 좋은 하루 되세요.",
        "{name}님께 {gift}를 준비했습니다.\n감사의 마음을 담았습니다.",
    ],
    "mz_slang": [
        "{name} ㅊㅋㅊㅋ 🎂\n{gift} flex 좀 해봤음 ㅋ\n취향 저격이면 인증 ㄱㄱ",
        "real talk {name}아\n{gift} 이거 요즘 핫함 🔥\n선물 레전드 각?",
        "{name}!! {gift} 도착~\n감동받고 스토리 올려줘 ㅋㅋ\n센스 인정?",
    ],
}

OCCASION_HOOKS: dict[str, str] = {
    "생일": "생일",
    "100일": "100일",
    "취업": "취업/이직",
    "집들이": "집들이",
    "감사": "감사",
    "위로": "위로",
    "그냥": "오늘",
    "기념일": "기념일",
    "명절": "명절",
    "여행": "여행",
}


def draft_message(
    *,
    recipient_name: str,
    gift_name: str,
    tone: MessageTone = "casual",
    occasion: str = "그냥",
) -> str:
    templates = TEMPLATES.get(tone, TEMPLATES["casual"])
    template = templates[hash(recipient_name + gift_name) % len(templates)]
    occ_label = OCCASION_HOOKS.get(occasion, occasion)
    return template.format(
        name=recipient_name,
        gift=gift_name,
        occasion=occ_label,
    )


def format_gift_card(
    gift_name: str,
    price_label: str,
    why: str,
    rank: int,
    *,
    link: str = "",
    mall_name: str = "",
) -> str:
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "🎁")
    lines = [
        f"{medal} **{gift_name}** ({price_label})",
        f"   └ {why}",
    ]
    if mall_name:
        lines.append(f"   🏪 {mall_name}")
    if link:
        lines.append(f"   🔗 {link}")
    return "\n".join(lines)
