"""수집한 기사를 SQLite에 누적 저장 (며칠치 이력 조회용)."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("news.db")


def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS news (
        link TEXT PRIMARY KEY, title TEXT, desc TEXT, dt TEXT,
        regions TEXT, categories TEXT, keywords TEXT, score INTEGER, important INTEGER)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_dt ON news(dt)")
    return con


def upsert(items):
    con = connect()
    with con:
        con.executemany(
            "INSERT OR REPLACE INTO news VALUES (?,?,?,?,?,?,?,?,?)",
            [(i["link"], i["title"], i["desc"], i["dt"], json.dumps(i["regions"], ensure_ascii=False),
              json.dumps(i["categories"], ensure_ascii=False), json.dumps(i["keywords"], ensure_ascii=False),
              i["score"], int(i["important"])) for i in items])
    con.close()


def load(since_iso):
    """since_iso(UTC ISO 문자열) 이후 기사 리스트(최신순)."""
    con = connect()
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM news WHERE dt >= ? ORDER BY dt DESC", (since_iso,)).fetchall()
    con.close()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("regions", "categories", "keywords"):
            d[k] = json.loads(d[k])
        d["important"] = bool(d["important"])
        out.append(d)
    return out
