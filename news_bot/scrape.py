"""구글 뉴스 RSS로 부산·울산·경남 기상/재해 뉴스 수집 (API 키 불필요)."""
import html
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import config as C

UA = {"User-Agent": "Mozilla/5.0 (busan-weather-news-dashboard)"}


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def fetch_rss(query, days):
    q = urllib.parse.quote(f"{query} when:{days}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return ET.fromstring(r.read())


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


def queries():
    n = C.KEYWORDS_PER_QUERY
    groups = [C.SEARCH_KEYWORDS[i:i + n] for i in range(0, len(C.SEARCH_KEYWORDS), n)]
    out = []
    for terms in C.SEARCH_REGIONS.values():
        region = "(" + " OR ".join(terms) + ")"
        for g in groups:
            kw = " OR ".join(f'"{k}"' if " " in k else k for k in g)
            out.append(f"{region} ({kw})")
    return out


def _search(args):
    q, days = args
    try:
        return list(fetch_rss(q, days).iter("item"))
    except Exception as e:
        print(f"fetch fail [{q}]: {e}", file=sys.stderr)
        return []


def collect(max_age_hours=None):
    """최근 기사 dict 리스트 (링크 기준 중복 제거, 오래된 순)."""
    hours = max_age_hours or C.FETCH_HOURS
    days = max(1, -(-hours // 24))
    now = datetime.now(timezone.utc)
    items = {}
    with ThreadPoolExecutor(3) as ex:
        for raw in ex.map(_search, [(q, days) for q in queries()]):
            for it in raw:
                try:
                    dt = parsedate_to_datetime(it.findtext("pubDate"))
                except Exception:
                    continue
                if now - dt > timedelta(hours=hours):
                    continue
                title = re.sub(r"\s+-\s+[^-]+$", "", clean(it.findtext("title")))
                regions, cats, kws, score = classify(title)
                if not regions or not cats:
                    continue
                link = it.findtext("link")
                items[link] = dict(link=link, title=title, desc="", dt=dt.isoformat(),
                                   regions=regions, categories=cats, keywords=kws,
                                   score=score, important=score >= C.IMPORTANT_MIN)
    return sorted(items.values(), key=lambda x: x["dt"])
