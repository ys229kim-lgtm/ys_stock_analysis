# /// script
# requires-python = ">=3.11"
# dependencies = ["langdetect"]
# ///
"""
뉴스 기사 전처리 스크립트.
- URL 기반 중복 제거
- 제목 유사도 기반 중복 제거 (85% 이상)
- 언어 감지 (ko/en/other)
- 기간 필터
- 중요도 스코어 계산
"""

import argparse
import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


def load_tier_list(tier_list_path: str) -> dict[str, int]:
    """media_tier_list.md에서 언론사 티어 파싱."""
    tier_map: dict[str, int] = {}
    path = Path(tier_list_path)
    if not path.exists():
        return tier_map

    current_tier = None
    for line in path.read_text(encoding="utf-8").splitlines():
        tier_match = re.match(r"#+\s*Tier\s*(\d+)", line, re.IGNORECASE)
        if tier_match:
            current_tier = int(tier_match.group(1))
            continue
        if current_tier and line.strip().startswith("-"):
            media_name = line.strip().lstrip("-").strip()
            if media_name:
                tier_map[media_name.lower()] = current_tier

    return tier_map


def detect_language(text: str) -> str:
    """langdetect가 없으면 한글 포함 여부로 fallback."""
    try:
        from langdetect import detect
        lang = detect(text)
        if lang == "ko":
            return "ko"
        if lang.startswith("en"):
            return "en"
        return "other"
    except Exception:
        pass

    korean_chars = len(re.findall(r"[가-힣]", text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return "other"
    if korean_chars / total_chars > 0.1:
        return "ko"
    ascii_chars = len(re.findall(r"[a-zA-Z]", text))
    if ascii_chars / total_chars > 0.3:
        return "en"
    return "other"


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str[:10], fmt)
        except ValueError:
            continue
    return None


def tier_score(source: str, tier_map: dict[str, int]) -> float:
    src_lower = source.lower().strip()
    tier = tier_map.get(src_lower)
    if tier is None:
        for name, t in tier_map.items():
            if name in src_lower or src_lower in name:
                tier = t
                break
    if tier == 1:
        return 1.0
    if tier == 2:
        return 0.6
    if tier == 3:
        return 0.3
    return 0.2


def text_length_score(article: dict, max_len: int) -> float:
    if article.get("paywall"):
        return 0.2
    full_text_file = article.get("full_text_file")
    if full_text_file:
        path = Path(full_text_file)
        if path.exists():
            length = len(path.read_text(encoding="utf-8", errors="ignore"))
            return min(length / max(max_len, 1), 1.0)
    snippet = article.get("snippet", "")
    return min(len(snippet) / 500, 0.5)


def keyword_density_score(article: dict, company: str) -> float:
    event_keywords = [
        "소송", "계약", "실적", "제재", "투자", "신사업", "인수", "합병", "파트너십",
        "수주", "매출", "영업이익", "손실", "리스크", "규제", "법원", "벌금",
        "lawsuit", "contract", "earnings", "penalty", "investment", "acquisition",
        "partnership", "revenue", "risk", "regulation",
    ]
    title = article.get("title", "").lower()
    company_lower = company.lower()
    company_short = company_lower[:3] if len(company_lower) >= 3 else company_lower

    score = 0.0
    if company_lower in title or company_short in title:
        score += 0.5
    for kw in event_keywords:
        if kw.lower() in title:
            score += 0.1
    return min(score, 1.0)


def calculate_importance_scores(articles: list[dict], company: str, tier_map: dict[str, int]) -> list[dict]:
    full_text_lengths = []
    for art in articles:
        full_text_file = art.get("full_text_file")
        if full_text_file and Path(full_text_file).exists():
            full_text_lengths.append(len(Path(full_text_file).read_text(encoding="utf-8", errors="ignore")))
        else:
            full_text_lengths.append(len(art.get("snippet", "")))

    max_len = max(full_text_lengths) if full_text_lengths else 1

    for i, art in enumerate(articles):
        t_score = tier_score(art.get("source", ""), tier_map) * 0.4
        l_score = (min(full_text_lengths[i] / max_len, 1.0) if not art.get("paywall") else 0.2) * 0.3
        k_score = keyword_density_score(art, company) * 0.3
        art["importance_score"] = round(t_score + l_score + k_score, 4)

    return articles


def dedup_by_url(articles: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    result = []
    for art in articles:
        url = art.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            result.append(art)
    return result


def dedup_by_title(articles: list[dict], threshold: float = 0.85) -> list[dict]:
    """유사 제목 중복 제거: 유사도 threshold 이상이면 최신 기사 1건 유지."""
    articles_sorted = sorted(
        articles,
        key=lambda a: parse_date(a.get("published_date")) or datetime.min,
        reverse=True,
    )
    kept: list[dict] = []
    for art in articles_sorted:
        title = art.get("title", "")
        is_dup = any(title_similarity(title, k.get("title", "")) >= threshold for k in kept)
        if not is_dup:
            kept.append(art)
    return kept


def filter_by_date(articles: list[dict], start: datetime | None, end: datetime | None) -> list[dict]:
    result = []
    for art in articles:
        d = parse_date(art.get("published_date"))
        if d is None:
            result.append(art)
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        result.append(art)
    return result


def main():
    parser = argparse.ArgumentParser(description="뉴스 기사 전처리")
    parser.add_argument("--input", required=True, help="입력 JSON 파일 경로")
    parser.add_argument("--output", required=True, help="출력 JSON 파일 경로")
    parser.add_argument("--company", required=True, help="기업명")
    parser.add_argument("--tier-list", default="", help="언론사 티어 목록 파일 경로")
    parser.add_argument("--start-date", default="", help="수집 시작일 YYYY-MM-DD")
    parser.add_argument("--end-date", default="", help="수집 종료일 YYYY-MM-DD")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] 입력 파일 없음: {input_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    articles: list[dict] = data.get("articles", [])
    print(f"[INFO] 원본 기사 수: {len(articles)}")

    tier_map = load_tier_list(args.tier_list) if args.tier_list else {}

    articles = dedup_by_url(articles)
    print(f"[INFO] URL 중복 제거 후: {len(articles)}")

    articles = dedup_by_title(articles, threshold=0.85)
    print(f"[INFO] 제목 유사도 중복 제거 후: {len(articles)}")

    for art in articles:
        text = art.get("title", "") + " " + art.get("snippet", "")
        art["language"] = detect_language(text)

    start_dt = parse_date(args.start_date) if args.start_date else None
    end_dt = parse_date(args.end_date) if args.end_date else None
    articles = filter_by_date(articles, start_dt, end_dt)
    print(f"[INFO] 기간 필터 후: {len(articles)}")

    articles = calculate_importance_scores(articles, args.company, tier_map)
    articles.sort(key=lambda a: a.get("importance_score", 0), reverse=True)

    data["articles"] = articles
    data["preprocessed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["article_count"] = len(articles)

    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 전처리 완료: {len(articles)}건 → {args.output}")

    if len(articles) < 20:
        print(f"[WARN] 기사 수 부족 ({len(articles)}건). 수집 기간 확장 또는 재수집 필요.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
