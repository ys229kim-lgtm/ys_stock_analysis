# sector_tag 매핑 (valuation-engine의 SECTOR_WEIGHTS 키와 동일)

| sector_tag | 대표 업종 / SIC 예 | 판정 기준 |
|------------|------------------|-----------|
| `growth_tech` | 클라우드·SaaS·AI 인프라, SIC 7372/7370 중 매출성장 20%+ | 높은 성장, FCF 마진 개선 중 |
| `mature_tech` | 성숙 소프트웨어·IT서비스·하드웨어 | 성장 한 자릿수, 안정 이익 |
| `semis_cycle` | 반도체·장비 (SIC 3674, 3559) | 재고·가격 사이클 지배 |
| `bank` | 은행·지주 (SIC 6021/6022) | 순이자마진·CET1 중심, P/B·ROTCE |
| `insurance` | 보험 (SIC 63xx) | 결합비율·P/B·ROE |
| `reit` | 리츠 (SIC 6798) | FFO/AFFO 필수 — 엔진은 P/FFO 미지원, `pe`로 AFFO/주를 넣고 `eps_for_pe_basis`에 명시 |
| `utility` | 전력·가스·수도 (SIC 49xx) | 규제 수익률, 배당 |
| `energy_cycle` | 석유가스 E&P·정유·서비스 (SIC 13xx, 29xx) | 유가 사이클, 정상화 이익 |
| `consumer_staples` | 식품·음료·생활용품 (SIC 20xx 등) | 안정 현금흐름·배당 |
| `consumer_discretionary` | 소매·레저·자동차·외식 | 소비 경기 민감 |
| `homebuilder_cyclical` | 주택 건설 (SIC 1531, 1521) | 금리·주택 수요 사이클, 자산가치(P/B) 중요 |
| `healthcare_pharma` | 제약·의료기기·서비스 | 현금창출 제약사 |
| `biotech_pipeline` | 적자 바이오 | 파이프라인 가치(rNPV는 엔진 외부에서 계산해 입력) |
| `industrial_cyclical` | 기계·항공우주·운송·건자재 | 경기 사이클 |
| `default` | 위에 해당 없음 | 범용 가중치 |

## 분류 절차
1. SEC `sicDescription`(fetch_filings.py 출력) 확인 → 후보 태그
2. 최근 3년 매출 성장·마진 변동성·배당성향으로 성장/성숙/사이클 판정
3. 최근 10-K 사업 설명으로 확인. 불확실하면 사용자에게 1회 질문
4. `secondary_tag`와 `classification_rationale` 기록
