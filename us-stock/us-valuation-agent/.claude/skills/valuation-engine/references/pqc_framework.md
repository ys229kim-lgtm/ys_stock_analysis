# 비즈니스모델 분석 프레임워크 — Price · Quantity · Cost (미국)

`biz_model_{날짜}_{TICKER}.json` 구조:
```json
{
  "ticker":"KBH",
  "price": {"summary":"...", "pricing_power":"price_setter|price_taker|mixed", "evidence":[{"fact":"...","source":"..."}]},
  "quantity": {"summary":"...", "volume_drivers":["..."], "evidence":[...]},
  "cost": {"summary":"...", "cogs_ratio_note":"...", "fixed_vs_variable":"...", "operating_leverage":"high|medium|low", "evidence":[...]},
  "moat": {"rating":"Wide|Narrow|None", "types":["브랜드","규모","전환비용","네트워크","원가","규제/라이선스"], "rationale":"..."},
  "strengths":["..."], "weaknesses":["..."], "structural_risks":["..."]
}
```

## 각 축에서 확인할 것
**Price**: ASP/단가 추이(YoY, 믹스), 가격 인상·인센티브(할인, 금리 바이다운, 클로징 코스트 지원), 경쟁 대비 포지셔닝, 가격 전가 한계(규제·정부 정책·재판매 시장). 수치는 최근 3~4개 분기.
**Quantity**: 핵심 볼륨 지표(인도량, 구독자, 출하량, 점포 수, 수주잔고), 선행지표(수주·주문·백로그), 전환율, 용량 제약(CAPA·부지), 지역/세그먼트 믹스.
**Cost**: 원가율(COGS/매출), 원자재·인건비·토지 비중, 고정비 vs 변동비, SG&A 비율 추이, 영업 레버리지(매출 변화 대비 영업이익 변화). 데이터가 없으면 "미산출(데이터 한계)"로 쓰고 대리 지표 제시.

## Moat 판정
- 증거 없이 Wide 금지. 최근 5~10년 ROIC/영업마진의 지속성, 점유율 추이, 가격 결정력의 실적 증거를 사용.
- 사이클 업종은 대부분 Narrow/None. 이유(전환비용 낮음, 가격 수용자 등)를 명시.

## 자기 검증
- 3축 모두 ≥3개 근거 항목 + 출처, Moat 근거 존재, 강점·약점 각 3개 이상, 최신 분기 수치 포함.
