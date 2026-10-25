# XBRL 개념 우선순위 (fetch_sec.py)

`fetch_sec.py`는 아래 us-gaap 개념을 **기간 단위로 병합**한다(같은 기간은 앞선 개념 우선, 없는 기간은 다음 개념으로 채움).

| 항목 | 개념 순서 |
|------|-----------|
| revenue | Revenues → RevenueFromContractWithCustomerExcludingAssessedTax → RevenueFromContractWithCustomerIncludingAssessedTax → SalesRevenueNet |
| cost_of_revenue | CostOfRevenue → CostOfGoodsAndServicesSold → CostOfGoodsSold |
| gross_profit | GrossProfit |
| operating_income | OperatingIncomeLoss |
| net_income | NetIncomeLoss → ProfitLoss |
| eps_diluted / eps_basic | EarningsPerShareDiluted / EarningsPerShareBasic (USD/shares) |
| operating_cf | NetCashProvidedByUsedInOperatingActivities |
| capex | PaymentsToAcquirePropertyPlantAndEquipment → PaymentsToAcquireProductiveAssets |
| dividends_paid | PaymentsOfDividendsCommonStock → PaymentsOfDividends |
| buybacks | PaymentsForRepurchaseOfCommonStock |
| equity | StockholdersEquity → ...IncludingPortionAttributableToNoncontrollingInterest |
| cash | CashAndCashEquivalentsAtCarryingValue → CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| debt | LongTermDebt → NotesPayable → DebtLongtermAndShorttermCombinedAmount → LongTermDebtNoncurrent → SeniorNotes |
| inventory | InventoryNet → InventoryRealEstate → InventoryFinishedGoodsNetOfReserves |
| shares (최신) | dei:EntityCommonStockSharesOutstanding |

## 한계와 대응
- **사용자 정의 태그**(회사 접두사, 예: `kbh:`)는 수집하지 않는다 → `missing_concepts`/`stale_concepts`로 보고되며 실적 발표자료로 보완.
  - 확인된 사례(KBH): 영업이익, 총마진, 차입금(Notes payable), 재고는 us-gaap 표준 태그 최신값이 없어 보완 필요.
- `stale_concepts`: 해당 개념의 최근 보고 기간이 기준일(매출/순이익 최신 기간)보다 200일(손익)/120일(재무상태) 이상 오래된 경우. 과거 값은 연간 시계열에 남지만 TTM·최신 대차대조표에는 쓰지 않는다.
- TTM = 최근 FY + 최근 YTD − 전년 동기 YTD (10-Q 누계 기준). 전년 동기 값이 없으면 TTM 생략.
- 4Q = FY − 9개월 누계 (10-Q 3Q 누계 필요).
- 재작성(restatement)이 있으면 같은 기간의 가장 최근 filed 값을 사용한다.
- SEC API 오류/레이트리밋: 요청 간 0.2초 이상 간격 권장(현재 스크립트는 호출 2회뿐).
