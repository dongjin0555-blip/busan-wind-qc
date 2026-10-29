"""부산·울산·경남 기상 이슈 뉴스 대시보드 (Streamlit + 네이버 뉴스 검색 API).

실행: streamlit run news_bot/app.py
키 설정: 환경변수 또는 .streamlit/secrets.toml 에
    NAVER_CLIENT_ID = "..."
    NAVER_CLIENT_SECRET = "..."
"""
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import config as C
import scrape

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="부산·울산·경남 기상 이슈 뉴스", page_icon="🌀", layout="wide")


def _load_keys():
    for k in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"):
        if not os.environ.get(k):
            try:
                os.environ[k] = st.secrets[k]
            except Exception:
                pass
    return all(os.environ.get(k) for k in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"))


@st.cache_data(ttl=600, show_spinner="네이버 뉴스 수집 중…")
def load(hours: int) -> pd.DataFrame:
    rows = scrape.collect(max_age_hours=hours)
    df = pd.DataFrame(rows, columns=["dt", "title", "link", "regions", "keywords", "desc"])
    if not df.empty:
        df["dt"] = pd.to_datetime(df["dt"], utc=True).dt.tz_convert(KST)
    return df.sort_values("dt", ascending=False).reset_index(drop=True)


st.title("🌀 부산·울산·경남 기상 이슈 뉴스")
st.caption("부산지방기상청 관측과 · 기상 이슈 및 기상에 의한 사회적 이슈 뉴스 모니터링 (네이버 뉴스, 10분 캐시)")

if not _load_keys():
    st.error("네이버 API 키가 없습니다. NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 을 "
             "환경변수 또는 .streamlit/secrets.toml 에 설정하세요.")
    st.stop()

with st.sidebar:
    st.header("필터")
    period = st.selectbox("기간", [6, 12, 24, 48, 72], index=2, format_func=lambda h: f"최근 {h}시간")
    regions = st.multiselect("지역", list(C.REGIONS), default=list(C.REGIONS))
    kw_sel = st.multiselect("키워드 (비우면 전체)", sorted(set(C.KEYWORDS)))
    q = st.text_input("제목 검색")
    if st.button("🔄 새로고침", width="stretch"):
        load.clear()
        st.rerun()

try:
    df = load(period)
except Exception as e:
    st.error(f"수집 실패: {e}")
    st.stop()

if not df.empty:
    m = df["regions"].apply(lambda r: any(x in regions for x in r))
    if kw_sel:
        m &= df["keywords"].apply(lambda k: any(x in kw_sel for x in k))
    if q:
        m &= df["title"].str.contains(q, case=False, regex=False)
    df = df[m]

c = st.columns(4)
c[0].metric("전체", len(df))
for col, r in zip(c[1:], C.REGIONS):
    col.metric(r, int(df["regions"].apply(lambda x: r in x).sum()) if len(df) else 0)

if df.empty:
    st.info("조건에 맞는 기사가 없습니다.")
    st.stop()

left, right = st.columns(2)
with left:
    st.subheader("키워드별 건수")
    st.bar_chart(df.explode("keywords")["keywords"].value_counts())
with right:
    st.subheader("시간대별 건수")
    st.bar_chart(df.set_index("dt").resample("1h").size())

st.subheader("기사 목록")
view = df.assign(시각=df["dt"].dt.strftime("%m/%d %H:%M"),
                 지역=df["regions"].apply(", ".join),
                 키워드=df["keywords"].apply(", ".join))
st.dataframe(
    view[["시각", "지역", "title", "키워드", "link"]],
    column_config={"title": "제목", "link": st.column_config.LinkColumn("링크", display_text="열기")},
    hide_index=True, width="stretch")
st.download_button("CSV 다운로드", view[["시각", "지역", "title", "키워드", "link"]].to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"weather_news_{datetime.now(KST):%Y%m%d_%H%M}.csv", mime="text/csv")
