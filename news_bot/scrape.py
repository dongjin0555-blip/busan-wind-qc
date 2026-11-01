"""연합뉴스 RSS에서 부산·울산·경남 기상/재해 뉴스를 골라 수집 (API 키 불필요)."""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import config as C

UA = {"User-Agent": "Mozilla/5.0 (busan-weather-news-dashboard)"}


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def fetch_rss(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return ET.fromstring(r.read())


def parse_dt(text):
    """RFC822 또는 'YYYY-MM-DD HH:MM:SS' 형식 (시간대 없으면 KST로 간주)."""
    try:
        dt = parsedate_to_datetime(text)
    except Exception:
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(text.strip(), fmt)
                break
            except Exception:
                pass
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
    return dt


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


def _fetch(url):
    try:
        return list(fetch_rss(url).iter("item"))
    except Exception as e:
        print(f"fetch fail [{url}]: {e}", file=sys.stderr)
        return []


def collect(max_age_hours=None):
    """최근 기사 dict 리스트 (링크 기준 중복 제거, 오래된 순)."""
    limit = timedelta(hours=max_age_hours or C.FETCH_HOURS)
    now = datetime.now(timezone.utc)
    items = {}
    for url in C.FEED_URLS:
        for it in _fetch(url):
            dt = parse_dt(it.findtext("pubDate") or "")
            if dt is None or now - dt > limit:
                continue
            title, desc = clean(it.findtext("title")), clean(it.findtext("description"))
            regions, cats, kws, score = classify(title + " " + desc)
            link = (it.findtext("link") or "").split("?")[0]
            if not regions or not cats or not link:
                continue
            items[link] = dict(link=link, title=title, desc=desc, dt=dt.isoformat(),
                               regions=regions, categories=cats, keywords=kws,
                               score=score, important=score >= C.IMPORTANT_MIN)
    return sorted(items.values(), key=lambda x: x["dt"])
