"""부산·울산·경남 기상 이슈 뉴스 스크랩 → 텔레그램 채널 전송."""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path

import config as C

SEEN_FILE = Path(__file__).with_name("seen.json")
UA = {"User-Agent": "Mozilla/5.0 (busan-weather-news-bot)"}


def fetch_rss(query):
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def collect():
    items = {}
    for region, names in C.REGIONS.items():
        for group in C.QUERY_GROUPS:
            query = f"({' OR '.join(names[:3])}) ({group})"
            try:
                root = fetch_rss(query)
            except Exception as e:
                print(f"fetch fail [{query}]: {e}", file=sys.stderr)
                continue
            for it in root.iter("item"):
                title = clean(it.findtext("title"))
                link = it.findtext("link")
                src = clean(it.findtext("source"))
                try:
                    dt = parsedate_to_datetime(it.findtext("pubDate"))
                except Exception:
                    continue
                if datetime.now(timezone.utc) - dt > timedelta(hours=C.MAX_AGE_HOURS):
                    continue
                # 제목 끝의 " - 언론사" 제거
                title = re.sub(r"\s+-\s+[^-]+$", "", title)
                text = title + " " + clean(it.findtext("description"))
                hit_regions = [r for r, ns in C.REGIONS.items() if any(n in text for n in ns)]
                if not hit_regions or not any(k.split()[0] in text for k in C.KEYWORDS):
                    continue
                items[link] = dict(title=title, link=link, src=src, dt=dt, regions=hit_regions)
            time.sleep(1)
    return sorted(items.values(), key=lambda x: x["dt"])


def send(token, chat_id, it):
    kst = it["dt"].astimezone(timezone(timedelta(hours=9))).strftime("%m/%d %H:%M")
    tags = " ".join("#" + r for r in it["regions"])
    msg = (f"📰 <b>{html.escape(it['title'])}</b>\n"
           f"{html.escape(it['src'])} · {kst}\n{tags}\n{html.escape(it['link'])}")
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode()
    urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30).read()


def main():
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    dry = not (token and chat_id)
    seen = json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}
    new = [i for i in collect() if i["link"] not in seen][-C.MAX_SEND_PER_RUN:]
    print(f"new items: {len(new)} (dry-run={dry})")
    for it in new:
        if dry:
            print(it["dt"].isoformat(), it["regions"], it["title"], it["src"])
        else:
            send(token, chat_id, it)
            time.sleep(1.5)
            seen[it["link"]] = it["dt"].isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    seen = {k: v for k, v in seen.items() if v > cutoff}
    if not dry:
        SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
