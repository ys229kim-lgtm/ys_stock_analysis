# 투자 시나리오 및 주가 전망 가이드

## 시나리오 구성 원칙

1. 3개 시나리오(Positive·Base·Negative) 각각에 **5개 에이전트 시각이 모두 반영**되어야 한다
2. 확률은 Industry agent 시나리오 확률을 기준값(앵커)으로 사용
3. Industry agent 누락 시 기본값: Positive 30% / Base 50% / Negative 20% → 리포트에 기본값 적용 명시
4. 나머지 에이전트(DART·Telegram·News·Valuation) 신호로 ±15%p 이내 보정

---

## 주가 범위 규칙 (하드 리밋)

| 시나리오 | 주가 하단 | 주가 상단 |
|---------|---------|---------|
| **Positive** | `fair_value_range.high` | `Telegram TP 최고치` |
| **Base** | `fair_value_range.low` | `fair_value_range.high` |
| **Negative** | 자유 (합리적 하방) | `fair_value_range.low` |

**특수 케이스: 현재 주가 > `fair_value_range.high`**  
→ 모든 시나리오 주가 범위가 현재주가 이하가 됨  
→ 리포트에 반드시 명시: "**현재 주가 고평가 구간 — 모든 시나리오에서 하방 압력**"

---

## 확률 보정 규칙

```
보정 방향:
  DART FCF 회복 신호     → +2~3%p (Positive 방향)
  DART Red Flag 현실화   → -2~3%p (Positive 방향, Negative 방향으로 +)
  Telegram Buy 비율 우세 → +1~2%p (Positive 방향)
  Telegram 컨센 하향     → -2~3%p (Positive 방향)
  News 진행 중 리스크 3+ → -3~5%p (Positive 방향)
  Valuation 고평가       → -2~3%p (Positive 방향)
  Valuation 저평가 15%+  → +2~3%p (Positive 방향)
```

**규칙:**
- 총 보정량 ±15%p 이내
- 보정량과 보정 근거를 각 시나리오 확률 옆에 명시
- 근거 없는 보정 금지
- 합계: Positive + Base + Negative = 100%

**표기 형식:**
```
Positive 40%
  (Industry 기준값 35%에서, DART FCF 회복 신호 +3%p, Telegram Buy 비율 우세 +2%p 보정)
```

---

## 섹션 7 작성 형식

### 7.1 시나리오별 전제 조건 및 주가 전망

**Positive Case 박스:**
```
[전제 조건]
 - 재무: {FCF 회복 조건}         ← DART
 - 산업: {업사이클 조건}          ← Industry
 - 촉매: {주요 이벤트 조건}       ← News + Telegram
 - 공시: {긍정 공시 조건}         ← Valuation

[예상 실적]  매출 {범위}% / 영업이익률 {범위}%p
[주가 전망]  {하단}원 ~ {상단}원 (현재주가 대비 +{X}%)
[핵심 모니터링] 이 시나리오의 진행을 확인하는 선행 지표
```

**Base Case 박스:**
```
[전제 조건]
 - 재무: {현재 수준 유지 조건}    ← DART
 - 산업: {완만한 회복 조건}       ← Industry
 - 촉매: {기존 계획 지속 조건}    ← News + Telegram
 - 공시: {특이 이벤트 없음}       ← Valuation

[예상 실적]  매출 {범위}% / 영업이익률 현 수준 유지
[주가 전망]  {하단}원 ~ {상단}원 (현재주가 대비 ±{X}%)
[핵심 모니터링] Base Case 이탈 신호 (위/아래 방향)
```

**Negative Case 박스:**
```
[전제 조건]
 - 재무: {FCF 악화, Red Flag 현실화 조건}  ← DART
 - 산업: {업사이클 지연, 공급 과잉 조건}   ← Industry
 - 촉매: {핵심 고객사 이탈, 리스크 현실화} ← News + Telegram
 - 공시: {유상증자, 대규모 손상 등}         ← Valuation

[예상 실적]  매출 {범위}% / 영업이익률 {범위}%p 하락
[주가 전망]  {하단}원 ~ {상단}원 (현재주가 대비 -{X}%)
[핵심 모니터링] 이 시나리오 진입 신호 (조기 경보 지표)
```

### 7.2 시나리오 간 전환 신호 (Trigger Watch)

```
- Positive → Base 하향 신호: {구체적 지표 또는 이벤트}
- Base → Negative 하향 신호: {구체적 지표 또는 이벤트}
- Negative → Base 상향 신호: {구체적 지표 또는 이벤트}
```

### 7.3 핵심 투자 포인트 (Key Takeaways)

```
가장 중요한 기회 요인 (1~3개):
1. {기회 요인 1}
2. {기회 요인 2}

가장 주의해야 할 리스크 (1~3개):
1. {리스크 1}
2. {리스크 2}

향후 3~6개월 내 확인해야 할 핵심 이벤트:
- {이벤트 1}: {예상 시점}
- {이벤트 2}: {예상 시점}
```

---

## 밸류에이션 섹션 6 작성 형식

### 6.2 6종 밸류에이션 결과 비교 테이블

| 방법 | 하단 | 중간 | 상단 | upside% |
|-----|-----|-----|-----|---------|
| DCF | | | | |
| PER | | | | |
| PBR | | | | |
| EV/EBITDA | | | | |
| DDM | 적용시 | 적용시 | 적용시 | |
| SOTP | 적용시 | | | |
| RIM | 적용시 | | | |
| **가중 평균** | | | | |

*val_results에 없는 방법은 "-" 처리, 적용 안 된 이유 각주*

### 6.4 현재 주가 위치 해석

- **저평가**: 현재주가 < fair_value_range.low
- **적정 범위**: fair_value_range.low ≤ 현재주가 ≤ fair_value_range.high
- **고평가**: 현재주가 > fair_value_range.high
