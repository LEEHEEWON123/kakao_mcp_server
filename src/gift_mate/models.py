from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Relationship = Literal[
    "친구",
    "베프",
    "썸",
    "연인",
    "직장동료",
    "선배",
    "후배",
    "부모님",
    "형제/자매",
]

Occasion = Literal[
    "생일",
    "100일",
    "취업",
    "집들이",
    "감사",
    "위로",
    "그냥",
    "기념일",
    "명절",
    "여행",
]

Vibe = Literal[
    "힙한",
    "실용",
    "감성",
    "킬러템",
    "밈맞춤",
    "MZ공감",
]

MessageTone = Literal[
    "casual",
    "funny",
    "heartfelt",
    "formal",
    "mz_slang",
]

BUDGET_LABELS: dict[str, tuple[int, int]] = {
    "커피값": (0, 10_000),
    "배민한끼": (10_000, 25_000),
    "네일/헤어": (25_000, 50_000),
    "신발한켤레": (50_000, 100_000),
    "flex": (100_000, 999_999_999),
}


@dataclass
class Gift:
    id: str
    name: str
    category: str
    price_min: int
    price_max: int
    relationships: list[str]
    occasions: list[str]
    vibes: list[str]
    description: str
    why_mz: str
    tags: list[str] = field(default_factory=list)

    @property
    def price_label(self) -> str:
        avg = (self.price_min + self.price_max) // 2
        if avg <= 10_000:
            return "커피값 (~1만)"
        if avg <= 25_000:
            return "배민한끼 (~2만)"
        if avg <= 50_000:
            return "네일/헤어 (~5만)"
        if avg <= 100_000:
            return "신발한켤레 (~10만)"
        return "flex (~10만+)"
