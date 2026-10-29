# 부산·울산·경남 기상 이슈 뉴스 대시보드

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

네이버 키: https://developers.naver.com → 애플리케이션 등록 → 사용 API "검색".
지역·키워드는 `config.py`에서 수정합니다.

## 배포
Streamlit Community Cloud에서 이 저장소의 `news_bot/app.py`를 지정하고,
Settings → Secrets에 위 두 값을 넣으면 URL로 접속 가능합니다.

`scrape.py` + `.github/workflows/news.yml`은 이전 텔레그램 전송용(수동 실행 전용)입니다.
