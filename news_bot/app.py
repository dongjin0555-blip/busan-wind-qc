"""부산·울산·경남 기상·재해 뉴스 대시보드 (Streamlit + 구글 뉴스 RSS + SQLite 이력).

실행: streamlit run news_bot/app.py
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import config as C
import db
import scrape

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="부산·울산·경남 기상·재해 뉴스", page_icon="🌀", layout="wide")


def in_hours(now=None) -> bool:
    now = now or datetime.now(KST)
    minutes = now.hour * 60 + now.minute
    return C.COLLECT_START_HOUR * 60 <= minutes <= C.COLLECT_END_HOUR * 60  # 종료 시각 정각까지 포함


def slot() -> int:
    """15분 단위 구간 번호 (캐시 키)."""
    return int(datetime.now(KST).timestamp() // (C.REFRESH_MINUTES * 60))


@st.cache_data(ttl=C.REFRESH_MINUTES * 60, show_spinner="구글 뉴스 수집 중…")
def refresh(_slot: int) -> int:
    """운영 시간 내에만 수집 후 DB에 누적 저장. 수집 건수 반환."""
    items = scrape.collect()
    db.upsert(items)
    return len(items)


def history(days: int) -> pd.DataFrame:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    df = pd.DataFrame(db.load(since), columns=[
        "dt", "title", "link", "desc", "regions", "categories", "keywords", "score", "important"])
    if not df.empty:
        df["dt"] = pd.to_datetime(df["dt"], utc=True).dt.tz_convert(KST)
    return df


st.title("🌀 부산·울산·경남 기상·재해 뉴스")
st.caption("부산지방기상청 관측과 · 기상 이슈, 화재·재해·사고, 교통 영향 뉴스 모니터링 "
           f"(구글 뉴스 · 매일 {C.COLLECT_START_HOUR:02d}:00~{C.COLLECT_END_HOUR:02d}:00 {C.REFRESH_MINUTES}분 간격 갱신 · DB 누적)")

with st.sidebar:
    st.header("필터")
    days = st.select_slider("조회 기간", [1, 2, 3, 7, 14, 30], value=1, format_func=lambda d: f"최근 {d}일")
    regions = st.multiselect("지역", list(C.REGIONS), default=list(C.REGIONS))
    cats = st.multiselect("카테고리", list(C.CATEGORIES), default=list(C.CATEGORIES))
    kw_sel = st.multiselect("키워드 (비우면 전체)", sorted(set(C.KEYWORDS)))
    q = st.text_input("제목 검색")
    if st.button("🔄 지금 새로 수집", width="stretch"):
        refresh.clear()
        st.rerun()

if in_hours():
    try:
        refresh(slot())
        st.caption(f"마지막 갱신 구간: {datetime.now(KST):%H:%M} 기준 (다음 갱신 {C.REFRESH_MINUTES}분 주기)")
    except Exception as e:
        st.warning(f"수집 실패 (저장된 이력만 표시합니다): {e}")
else:
    st.info(f"수집 운영 시간({C.COLLECT_START_HOUR:02d}:00~{C.COLLECT_END_HOUR:02d}:00) 외입니다. "
            "저장된 이력만 표시합니다.")

# 열려 있는 화면을 주기적으로 다시 불러와 새 기사를 반영
@st.fragment(run_every=f"{C.REFRESH_MINUTES}m")
def auto_refresh():
    if st.session_state.get("_ticked"):
        st.rerun()  # 타이머 발동 시 전체 앱을 다시 실행
    st.session_state["_ticked"] = True


auto_refresh()

df = history(days)
if not df.empty:
    m = df["regions"].apply(lambda r: any(x in regions for x in r))
    m &= df["categories"].apply(lambda c: any(x in cats for x in c))
    if kw_sel:
        m &= df["keywords"].apply(lambda k: any(x in kw_sel for x in k))
    if q:
        m &= df["title"].str.contains(q, case=False, regex=False)
    df = df[m]

if df.empty:
    st.info("조건에 맞는 기사가 없습니다.")
    st.stop()

c = st.columns(5)
c[0].metric("전체", len(df))
c[1].metric("🚨 주요", int(df["important"].sum()))
for col, r in zip(c[2:], C.REGIONS):
    col.metric(r, int(df["regions"].apply(lambda x: r in x).sum()))


def fmt(frame):
    return frame.assign(시각=frame["dt"].dt.strftime("%m/%d %H:%M"),
                        지역=frame["regions"].apply(", ".join),
                        분류=frame["categories"].apply(", ".join),
                        키워드=frame["keywords"].apply(lambda k: ", ".join(dict.fromkeys(k))))


COLS = {"title": "제목", "link": st.column_config.LinkColumn("링크", display_text="열기")}
SHOW = ["시각", "지역", "분류", "title", "키워드", "link"]

imp = df[df["important"]].sort_values(["score", "dt"], ascending=False)
st.subheader(f"🚨 주요 기사 ({len(imp)}건)")
st.caption("특보·경보·주의보 발효, 대피, 인명피해, 산불·붕괴 등 중요 용어 점수가 높은 기사 (기준: config.py)")
if imp.empty:
    st.write("현재 주요 기사가 없습니다.")
else:
    for _, r in imp.head(10).iterrows():
        st.markdown(f"**[{r['title']}]({r['link']})**  \n"
                    f"{r['dt']:%m/%d %H:%M} · {', '.join(r['regions'])} · {', '.join(r['categories'])}"
                    f" · 점수 {r['score']}")
        if r["desc"]:
            st.caption(r["desc"])

left, right = st.columns(2)
with left:
    st.subheader("키워드별 건수")
    st.bar_chart(df.explode("keywords")["keywords"].value_counts().head(20))
with right:
    st.subheader("일별/시간별 건수")
    st.bar_chart(df.set_index("dt").resample("1D" if days > 3 else "1h").size())

if days > 1:
    st.subheader("일별 지역 추이")
    d = df.explode("regions").assign(일자=lambda x: x["dt"].dt.strftime("%m/%d"))
    st.bar_chart(d.groupby(["일자", "regions"]).size().unstack(fill_value=0))

st.subheader("전체 기사 목록")
view = fmt(df)
st.dataframe(view[SHOW], column_config=COLS, hide_index=True, width="stretch")
st.download_button("CSV 다운로드", view[SHOW].to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"weather_news_{datetime.now(KST):%Y%m%d_%H%M}.csv", mime="text/csv")
