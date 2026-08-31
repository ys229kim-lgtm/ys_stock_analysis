# 밸류에이션 수식 정의

## 1. DCF (Discounted Cash Flow)

### 수식
```
FCF_t = FCF_0 × (1 + g_5y)^t  (t = 1~5)

PV_FCF = Σ FCF_t / (1 + WACC)^t

Terminal_Value = FCF_5 × (1 + g_term) / (WACC - g_term)
PV_TV = Terminal_Value / (1 + WACC)^5

EV_intrinsic = PV_FCF + PV_TV
Equity_Value = EV_intrinsic - Net_Debt + Cash
Per_Share = Equity_Value / Shares_Outstanding
```

### 민감도 범위
- 하단: Per_Share × 0.90 (WACC +1%p 또는 g −0.5%p 시나리오)
- 상단: Per_Share × 1.10 (WACC -1%p 또는 g +0.5%p 시나리오)

### 주의
- FCF = NOPAT + D&A - CapEx - ΔWorking Capital
- NOPAT = 영업이익 × (1 - 유효세율)
- Net_Debt = 총차입금 - 현금성자산
- 분모(WACC - g_term) > 0 검증 필수

---

## 2. PER (Price-to-Earnings Ratio)

### 수식
```
Intrinsic_Price = Peer_PER × EPS_TTM
```

### 민감도 범위
- 하단: Peer_PER × EPS × 0.90 (업종 하단 PER 또는 EPS -10%)
- 상단: Peer_PER × EPS × 1.10

### 주의
- EPS_TTM: 최근 4분기 합산 (annualized)
- Peer_PER: 동종 업종 상장기업 중앙값 또는 평균 (출처 명시)
- EPS < 0 시 PER 미적용

---

## 3. PBR (Price-to-Book Ratio)

### 수식
```
Intrinsic_Price = Peer_PBR × BPS
BPS = 자본총계 / 발행주식수
```

### 민감도 범위
- 하단: Peer_PBR × BPS × 0.90
- 상단: Peer_PBR × BPS × 1.10

### 주의
- 금융업(은행·보험)은 PBR 우선 적용
- BPS < 0 시 PBR 미적용

---

## 4. PSR (Price-to-Sales Ratio)

### 수식
```
Intrinsic_Price = Peer_PSR × Revenue_Per_Share
Revenue_Per_Share = 연매출 / 발행주식수
```

### 민감도 범위
- 하단: Peer_PSR × RPS × 0.90
- 상단: Peer_PSR × RPS × 1.10

### 주의
- 적자기업, 초기 성장주에 특히 유용
- Revenue > 0 검증 필수

---

## 5. EV/EBITDA

### 수식
```
Implied_EV = Peer_EV_EBITDA × EBITDA
Equity_Value = Implied_EV - Net_Debt
Per_Share = Equity_Value / Shares_Outstanding
```

### 민감도 범위
- 하단: (Peer_EV_EBITDA × EBITDA × 0.90 - Net_Debt) / Shares
- 상단: (Peer_EV_EBITDA × EBITDA × 1.10 - Net_Debt) / Shares

### 주의
- EBITDA < 0 시 미적용
- 자본집약적 산업(반도체·철강·에너지)에 높은 가중치

---

## 6. DDM (Dividend Discount Model)

### 적용 조건 (모두 충족 시)
1. DPS_last > 0
2. 배당성향 = DPS / EPS < 100%
3. ROE > Ke

### 수식
```
Ke = WACC  (단순화, 부채 없는 경우)
DPS_1 = DPS_last × (1 + g_term)
Intrinsic_Price = DPS_1 / (Ke - g_term)
```

### 민감도 범위
- 하단: DPS_1 / ((Ke + 0.01) - g_term)
- 상단: DPS_1 / ((Ke - 0.01) - g_term)

### 주의
- Ke - g_term > 0 검증 필수 (분모 음수 방지)
- 배당이 안정적이지 않으면 신뢰도 낮음 표기

---

## 7. RIM (Residual Income Model)

### 수식
```
RI_t = (ROE - Ke) × BPS_{t-1}
BPS_t = BPS_{t-1} × (1 + ROE × (1 - 배당성향))

PV_RI = Σ RI_t / (1 + Ke)^t  (t = 1~5)

# 5년 이후: ROE를 (ROE + Ke)/2로 fade
Fade_ROE = (ROE + Ke) / 2
Terminal_RI = (Fade_ROE - Ke) × BPS_5
PV_Terminal_RI = Terminal_RI / (Ke - g_term) / (1 + Ke)^5

Intrinsic = BPS_0 + PV_RI + PV_Terminal_RI
```

### 주의
- ROE < Ke 이면 잔여이익 음수 → 적정가 < BPS
- 금융업(장부가 의미 있는 경우)에 특히 적합
- 배당성향 미확인 시 30% 가정

---

## 가중 평균 적정가 계산

```
Weighted_Mid = Σ(그룹별_중간값 × 그룹_가중치)

그룹:
- DCF·RIM 그룹 (dcf_rim 가중치)
- 상대가치 그룹 = PER + PBR + PSR + EV/EBITDA 평균 (relative 가중치)
- DDM 그룹 (ddm 가중치, 미적용 시 dcf_rim/relative에 50:50 재배분)
```
