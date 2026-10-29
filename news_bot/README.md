# 부산·울산·경남 기상·재해 뉴스 대시보드

기상 이슈, 화재·재해·사고, 교통 영향 뉴스를 네이버 뉴스 검색 API로 수집해 Streamlit으로 보여줍니다.

## 실행
```bash
pip install -r news_bot/requirements.txt
mkdir -p news_bot/.streamlit
cat > news_bot/.streamlit/secrets.toml <<'T'
NAVER_CLIENT_ID = "발급받은 ID"
NAVER_CLIENT_SECRET = "발급받은 Secret"
T
streamlit run news_bot/app.py
```
(secrets.toml 대신 환경변수 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`도 가능)
네이버 키: https://developers.naver.com → 애플리케이션 등록 → 사용 API "검색"

## 기능
- 카테고리: 기상 / 재해·사고(화재, 산불, 붕괴, 침수, 인명피해 등) / 교통·생활
- 🚨 주요 기사: 특보·경보·주의보 발효, 대피, 인명피해, 산불 등 점수 기준으로 상단 강조
- 이력: 수집한 기사는 `news_bot/news.db`(SQLite)에 누적. 사이드바에서 최대 30일 조회
- 필터: 기간·지역·카테고리·키워드·제목 검색, CSV 다운로드

지역·키워드·주요 기사 점수는 `config.py`에서 수정합니다.

## 주의
- 이력은 앱이 실행되어 있는 동안(운영 시간 09~18시, 15분 주기)만 쌓입니다. 상시 수집이 필요하면 상시 실행되는 서버에서 띄우세요.
- Streamlit Community Cloud는 재시작 시 파일(news.db)이 초기화될 수 있습니다.
