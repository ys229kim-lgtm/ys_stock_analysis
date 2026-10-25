# 밸류에이션 산식 (calculate_valuation.py 구현 기준)

| 방법 | 산식 | low / mid / high | 적용 불가 조건 |
|------|------|------------------|----------------|
| pe | `eps_for_pe` x PER | 입력 멀티플의 low/mid/high (스칼라면 +-15%) | EPS ≤ 0 |
| pb | BPS x PBR | 입력 멀티플 | BPS ≤ 0 |
| ps | 주당매출 x PSR | 입력 멀티플 | 주당매출 없음 |
| ev_ebitda | (멀티플 x EBITDA − 순차입) / 주식수 | 입력 멀티플 | EBITDA ≤ 0 |
| pe_norm | 정상화 EPS(low/mid/high) x 멀티플 | 각각 대응 | 정상화 EPS 없음 |
| dcf | 5년 FCF 성장 후 Gordon 영구가치, (EV − 순차입)/주식수 | WACC +-1%p, g +-0.5%p 격자의 최소/최대 | FCF ≤ 0, WACC − g < 2%p, 결과 ≤ 0 |
| ddm | DPS1 / (Ke − g) | g +-0.5%p | 무배당, 배당성향 ≥ 100%, Ke − g < 2%p |
| rim | BV0 + Σ (ROE_t − Ke) x BV_{t−1}/(1+Ke)^t + 잔여이익 지속 종가 | Ke +-1%p | BPS/ROE/Ke/장기 ROE 없음 |

## RIM 세부
- ROE는 현재 ROE에서 `rim_roe_long_run`으로 `rim_years`(기본 5년)에 걸쳐 선형 수렴.
- BV 성장 = ROE x (1 − payout). 종가 = RI_N x ω / (1 + Ke − ω), ω = `rim_persistence`(기본 0.6).
- ROE < Ke 인 기업은 RIM이 BPS 아래로 나올 수 있음(음의 잔여이익) — 정상 동작이며 해석에서 설명.

## 가중 평균
- 요청 가중치 중 적용된 방법만 재정규화해 low/mid/high 각각 가중합. `fair_value_range = {weighted low, weighted high}`.
- `position`: 현재가 < low → 저평가, > high → 고평가, 그 외 → 적정 범위.
- `mid_dispersion_ratio` = 적용 방법 mid의 최대/최소. 2 초과 시 flag.

## 해석 시 주의
- 멀티플 방법들은 같은 컨센서스 이익·동종 중앙값에 의존해 서로 독립적이지 않다.
- P/B는 ROE가 Ke 아래면 1배 미만 거래가 정당화될 수 있다(자산가치 할인 ≠ 자동 저평가).
- 사이클 저점의 정상화 EPS는 가장 주관적 — 낮은 가중치와 보수적 멀티플을 쓴다.
- 홈빌더·건설: 이자 자본화로 EBITDA/EV 계열이 왜곡되므로 기본 제외.
