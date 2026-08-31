# korea-stock-mcp 사용 가이드

## 현재가 및 시장 데이터

### get_stock_base_info
```
mcp__korea-stock-mcp__get_stock_base_info
  종목코드: "005930"  (6자리, 문자열)
```

**반환 필드:**
| 필드 | 설명 | val_inputs 매핑 |
|------|------|--------------|
| 현재가 | 현재 주가 (원) | current_price |
| 시가총액 | 억원 단위 | market.market_cap |
| 52주고 | 52주 최고가 | 참고용 |
| 52주저 | 52주 최저가 | 참고용 |
| 거래량 | 당일 거래량 | 참고용 |

### get_stock_trade_info
```
mcp__korea-stock-mcp__get_stock_trade_info
  종목코드: "005930"
```

**반환 필드:**
| 필드 | 설명 | val_inputs 매핑 |
|------|------|--------------|
| PER | Price/Earnings | market.per_exchange |
| PBR | Price/Book | market.pbr_exchange |
| EPS | 주당순이익 | financials.eps_ttm (보완용) |
| BPS | 주당순자산 | financials.book_value_per_share (보완용) |
| 배당수익률 | % | 참고용 |

---

## 주의사항

1. **종목코드 형식:** 6자리 문자열 (예: "005930", "000660")
2. **장 마감 후:** 당일 종가 기준 데이터 반환
3. **코스피 vs 코스닥:** 동일한 툴로 조회 가능, 코드 기반 자동 구분
4. **PER/PBR 없음:** 적자 기업은 PER = None 반환 → EPS로 직접 계산

---

## DART MCP 재무 수집 (보완용)

financial-agent 데이터 없을 때:
```
mcp__dart-mcp__search_disclosure
  corp_code: {8자리 DART corp_code}
  bgn_de: "{1년 전 YYYYMMDD}"
  end_de: "{오늘 YYYYMMDD}"
  pblntf_ty: "A"  // 정기공시
```

8자리 corp_code 조회:
```
mcp__dart-mcp__search_business_information
  company_name: "{기업명}"
→ 결과에서 corp_code 추출
```

---

## 베타 수집 방법

### 1순위: 웹 검색
```
firecrawl_search
  query: "삼성전자 005930 베타 beta"
```

### 2순위: 네이버 금융 URL
```
https://finance.naver.com/item/main.naver?code={종목코드}
→ "투자지표" 섹션에서 베타 확인
```

### 3순위: 업종 기본값 적용
industry_weight_table.md 참조
