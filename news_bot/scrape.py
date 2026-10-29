"""네이버 뉴스 검색 API로 부산·울산·경남 기상/재해 뉴스 수집."""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import config as C


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def naver_search(query):
    url = "https://openapi.naver.com/v1/search/news.json?" + urllib.parse.urlencode(
        {"query": query, "display": 100, "sort": "date"})
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["items"]


def classify(text):
    """(지역, 카테고리, 키워드, 중요도 점수) 반환."""
    regions = [r for r, ns in C.REGIONS.items() if any(n in text for n in ns)]
    cats, kws = [], []
    for cat, ks in C.CATEGORIES.items():
        hit = [k for k in ks if k in text]
        if hit:
            cats.append(cat)
            kws += hit
    score = sum(w for t, w in C.IMPORTANT_TERMS.items() if t in text)
    return regions, cats, kws, score


def _search(q):
    try:
        return naver_search(q)
    except Exception as e:
        print(f"fetch fail [{q}]: {e}", file=sys.stderr)
        return []


def collect(max_age_hours=None):
    """신규/최근 기사 dict 리스트 (링크 기준 중복 제거)."""
    queries = [f"{r} {k}" for r in C.SEARCH_REGIONS for k in C.SEARCH_KEYWORDS]
    now = datetime.now(timezone.utc)
    limit = timedelta(hours=max_age_hours or C.FETCH_HOURS)
    items = {}
    with ThreadPoolExecutor(4) as ex:
        for raw in ex.map(_search, queries):
            for it in raw:
                dt = parsedate_to_datetime(it["pubDate"])
                if now - dt > limit:
                    continue
                title, desc = clean(it["title"]), clean(it["description"])
                regions, cats, kws, score = classify(title + " " + desc)
                if not regions or not cats:
                    continue
                link = it["link"] or it["originallink"]
                items[link] = dict(link=link, title=title, desc=desc, dt=dt.isoformat(),
                                   regions=regions, categories=cats, keywords=kws,
                                   score=score, important=score >= C.IMPORTANT_MIN)
    return sorted(items.values(), key=lambda x: x["dt"])
