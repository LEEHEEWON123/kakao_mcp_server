# 🎁 기프트메이트 (Gift Mate) — 선물 고민 종결 MCP

MZ 감성 선물 큐레이터 MCP 서버. [AGENTIC PLAYER 10](https://b.kakao.com/views/PlayMCP/AGENTIC_PLAYER_10) / [PlayMCP](https://playmcp.kakao.com) 출품용.

## 한 줄 소개

> "베프 생일, 3만원대, 감성적인 거" → 선물 TOP3 + 카톡 메시지 초안까지.

## MCP Tools (4개)

| Tool | 설명 |
|------|------|
| `recommend_gift` | 관계·상황·예산·vibe 기반 선물 추천 |
| `draft_gift_message` | 카톡/DM용 메시지 초안 (5가지 tone) |
| `compare_gifts` | 선물 A vs B MZ 관점 비교 |
| `gift_by_vibe` | vibe만으로 빠른 추천 |

## PlayMCP 등록 정보 (초안)

- **서버 이름**: 기프트메이트 — 선물 고민 종결
- **Endpoint**: `https://<your-domain>/mcp`
- **스타터 메시지**:
  ```
  뭐 사줄지 고민이야? 🎁
  누구한테, 어떤 상황(생일/취업/100일/그냥), 예산(커피값~flex), vibe(힙한/감성/밈맞춤) 알려줘!
  ```

## 로컬 실행

```bash
cd kakao_mcp_server
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 서버 실행 (PYTHONPATH=src 필요)
PYTHONPATH=src uvicorn gift_mate.server:app --host 0.0.0.0 --port 8080
```

- Health: http://localhost:8080/health
- MCP endpoint: http://localhost:8080/mcp

## Docker

```bash
docker build -t gift-mate-mcp .
docker run -p 8080:8080 gift-mate-mcp
```

## 카카오 클라우드 배포

1. Dockerfile로 이미지 빌드 후 카카오 클라우드 MCP Endpoint에 배포
2. PlayMCP 콘솔 → 새 MCP 서버 등록 → Endpoint URL 입력
3. 임시 등록으로 테스트 → **등록 및 심사 요청**
4. 심사 통과 후 **전체 공개** → [Player 예선 참여](https://b.kakao.com/views/PlayMCP/AGENTIC_PLAYER_10)

## 예산 키워드

| 키워드 | 범위 |
|--------|------|
| 커피값 | ~1만 |
| 배민한끼 | 1~2.5만 |
| 네일/헤어 | 2.5~5만 |
| 신발한켤레 | 5~10만 |
| flex | 10만+ |

## vibe 키워드

`힙한` · `실용` · `감성` · `킬러템` · `밈맞춤` · `MZ공감`

## 데모 시나리오

```
유저: "첫 출근한 후배한테 3만원대 실용적인 선물 추천해줘"
→ recommend_gift(relationship=후배, occasion=취업, budget=배민한끼, vibe=실용)

유저: "미니 향수 듀오로 카톡 메시지 mz_slang 톤으로 써줘"
→ draft_gift_message(recipient_name=민수, gift_name=미니 향수, tone=mz_slang)
```

## 프로젝트 구조

```
src/gift_mate/
├── server.py       # FastMCP + FastAPI
├── recommender.py  # 추천 엔진
├── messages.py     # MZ 톤 메시지 템플릿
├── models.py
└── data/gifts.json # 큐레이션 선물 DB (30종)
```

## 본선 확장 아이디어 (Kakao Tools Widget)

- 선물 카드 UI>
 3장 슬라이드 UI
- 카카오 선물하기 검색 링크 연동
- "오늘의 vibe" 랜덤 선물 룰렛
