# DART API 필드 매핑 가이드

## search_detailed_financial_data 주요 필드

| DART 계정명 | 표준 필드명 | 재무제표 |
|------------|-----------|---------|
| 매출액 / 수익(매출액) | revenue | 손익계산서 |
| 영업이익(손실) | operating_profit | 손익계산서 |
| 당기순이익(손실) | net_income | 손익계산서 |
| 자산총계 | total_assets | 재무상태표 |
| 자본총계 | total_equity | 재무상태표 |
| 부채총계 | total_debt | 재무상태표 |
| 유동자산 | current_assets | 재무상태표 |
| 유동부채 | current_liabilities | 재무상태표 |
| 영업활동현금흐름 | operating_cf | 현금흐름표 |
| 투자활동현금흐름 | investing_cf | 현금흐름표 |
| 재무활동현금흐름 | financing_cf | 현금흐름표 |
| 유형자산의취득 | capex | 투자CF 세부 |
| 이자비용 | interest_expense | 주석 또는 CF |

## XBRL contextRef 패턴
- 연결 당기: `CFY{YYYY}.FY_ifrs-full_ConsolidatedMember`
- 별도 당기: `CFY{YYYY}.FY_ifrs-full`

## 단위 자동 인식
| decimals 값 | 의미 |
|------------|------|
| -6 | 백만원 |
| -8 | 억원 (가장 흔함) |
| -9 | 십억원 |

판별 불가 시: **억원 기본값** 가정 후 경고 로그.

## 공시 지연 처리
- 사업보고서 제출 기한: 3월 말 (12월 결산 기준)
- `end_date` = 오늘 + 95일로 설정하면 지연 공시 포함 가능

## 연결/별도 판단
1. search_detailed_financial_data 결과에 `ConsolidatedMember` 포함 확인
2. 없으면 별도 기준 재수집 → `report_type: "별도"` 표기
