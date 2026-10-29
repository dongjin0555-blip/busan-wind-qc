"""새 기사를 텔레그램 채널로 전송 (GitHub Actions에서 15분마다 실행).

환경변수: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (없으면 전송 없이 출력만 하는 dry-run)
전송 이력: news_bot/sent.json (링크 -> 기사 시각), 7일 보관
"""
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import config as C
import scrape

SENT_FILE = Path(__file__).with_name("sent.json")
KST = timezone(timedelta(hours=9))
MAX_PER_RUN = 20       # 1회 최대 전송 수
FIRST_RUN_HOURS = 3    # 이력 파일이 없을 때(첫 실행)는 최근 N시간 기사만 전송


def tg_send(token, chat_id, text):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    for _ in range(3):
        try:
            urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30).read()
            return
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(json.load(e).get("parameters", {}).get("retry_after", 5) + 1)
    raise RuntimeError("telegram rate limit")


def format_item(it):
    dt = datetime.fromisoformat(it["dt"]).astimezone(KST).strftime("%m/%d %H:%M")
    tags = " ".join("#" + r for r in it["regions"]) + " " + " ".join(
        "#" + c.replace("·", "") for c in it["categories"])
    head = "🚨 " if it["important"] else "📰 "
    return (f"{head}<b>{html.escape(it['title'])}</b>\n{dt}  {tags}\n{html.escape(it['link'])}")


def main():
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    dry = not (token and chat_id)
    first = not SENT_FILE.exists()
    sent = {} if first else json.loads(SENT_FILE.read_text())

    items = scrape.collect()
    if first:
        limit = (datetime.now(timezone.utc) - timedelta(hours=FIRST_RUN_HOURS)).isoformat()
        for it in items:  # 첫 실행: 오래된 기사는 보낸 것으로 처리해 폭주 방지
            if it["dt"] < limit:
                sent[it["link"]] = it["dt"]
    new = [i for i in items if i["link"] not in sent]
    new.sort(key=lambda i: i["dt"])
    new = new[-MAX_PER_RUN:]
    print(f"collected={len(items)} new={len(new)} dry_run={dry}")

    for it in new:
        if dry:
            print(format_item(it).replace("\n", " | "))
            continue
        tg_send(token, chat_id, format_item(it))
        sent[it["link"]] = it["dt"]
        time.sleep(1.5)

    if not dry:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        sent = {k: v for k, v in sent.items() if v > cutoff}
        SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
