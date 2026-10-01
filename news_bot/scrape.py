"""부산·울산·경남 기상 이슈 뉴스 스크랩 → 텔레그램 채널 전송 (네이버 뉴스 검색 API).

python scrape.py          # 신규 기사 즉시 전송
python scrape.py summary  # 최근 24시간 요약본 전송 (매일 17:00 KST)
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import config as C

SEEN_FILE = Path(__file__).with_name("seen.json")
KST = timezone(timedelta(hours=9))


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


def collect():
    items = {}
    now = datetime.now(timezone.utc)
    for region in C.SEARCH_REGIONS:
        for kw in C.SEARCH_KEYWORDS:
            try:
                raw = naver_search(f"{region} {kw}")
            except Exception as e:
                print(f"fetch fail [{region} {kw}]: {e}", file=sys.stderr)
                continue
            for it in raw:
                dt = parsedate_to_datetime(it["pubDate"])
                if now - dt > timedelta(hours=C.MAX_AGE_HOURS):
                    continue
                title = clean(it["title"])
                text = title + " " + clean(it["description"])
                regions = [r for r, ns in C.REGIONS.items() if any(n in text for n in ns)]
                if not regions or not any(k.split()[0] in text for k in C.KEYWORDS):
                    continue
                link = it["link"] or it["originallink"]
                items[link] = dict(title=title, link=link, dt=dt, regions=regions)
            time.sleep(0.15)
    return sorted(items.values(), key=lambda x: x["dt"])


def tg(token, chat_id, msg):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30).read()
    time.sleep(1.5)


def send_item(token, chat_id, it):
    kst = it["dt"].astimezone(KST).strftime("%m/%d %H:%M")
    tags = " ".join("#" + r for r in it["regions"])
    tg(token, chat_id, f"📰 <b>{html.escape(it['title'])}</b>\n{kst}  {tags}\n{html.escape(it['link'])}")


def load_seen():
    return json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}


def run_realtime(token, chat_id):
    seen = load_seen()
    new = [i for i in collect() if i["link"] not in seen][-C.MAX_SEND_PER_RUN:]
    dry = not (token and chat_id)
    print(f"new items: {len(new)} (dry-run={dry})")
    for it in new:
        if dry:
            print(it["dt"].isoformat(), it["regions"], it["title"])
            continue
        send_item(token, chat_id, it)
        seen[it["link"]] = dict(t=it["title"], r=it["regions"], d=it["dt"].isoformat())
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    seen = {k: v for k, v in seen.items() if v["d"] > cutoff}
    if not dry:
        SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=0))


def run_summary(token, chat_id):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=C.SUMMARY_HOURS)).isoformat()
    rows = sorted((dict(v, link=k) for k, v in load_seen().items() if v["d"] > cutoff),
                  key=lambda x: x["d"])
    today = datetime.now(KST).strftime("%Y-%m-%d")
    head = f"📋 <b>{today} 17:00 기상 이슈 뉴스 요약</b> (최근 {C.SUMMARY_HOURS}시간, {len(rows)}건)\n"
    blocks = [head]
    for region in C.REGIONS:
        sub = [r for r in rows if region in r["r"]]
        if not sub:
            continue
        blocks.append(f"\n<b>■ {region} ({len(sub)}건)</b>")
        for r in sub:
            hhmm = datetime.fromisoformat(r["d"]).astimezone(KST).strftime("%H:%M")
            blocks.append(f'• {hhmm} <a href="{html.escape(r["link"])}">{html.escape(r["t"])}</a>')
    if not rows:
        blocks.append("\n해당 기간 수집된 기상 이슈 기사가 없습니다.")
    if not (token and chat_id):
        print("\n".join(blocks))
        return
    buf = ""
    for b in blocks:  # 텔레그램 4096자 제한 분할
        if len(buf) + len(b) + 1 > 3800:
            tg(token, chat_id, buf)
            buf = ""
        buf += b + "\n"
    tg(token, chat_id, buf)


if __name__ == "__main__":
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    (run_summary if sys.argv[1:] == ["summary"] else run_realtime)(token, chat_id)
