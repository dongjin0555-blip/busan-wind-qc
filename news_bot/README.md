# 부산·울산·경남 기상·재해 뉴스 대시보드

기상 이슈, 화재·재해·사고, 교통 영향 뉴스를 연합뉴스 RSS로 수집해 Streamlit으로 보여줍니다.

## 실행 (API 키 불필요)
```bash
pip install -r news_bot/requirements.txt
streamlit run news_bot/app.py
```
브라우저에서 http://localhost:8501 — 연합뉴스 RSS를 사용하므로 계정/키가 필요 없습니다.

## 기능
- 카테고리: 기상 / 재해·사고(화재, 산불, 붕괴, 침수, 인명피해 등) / 교통·생활
- 🚨 주요 기사: 특보·경보·주의보 발효, 대피, 인명피해, 산불 등 점수 기준으로 상단 강조
- 이력: 수집한 기사는 `news_bot/news.db`(SQLite)에 누적. 사이드바에서 최대 30일 조회
- 필터: 기간·지역·카테고리·키워드·제목 검색, CSV 다운로드

지역·키워드·주요 기사 점수는 `config.py`에서 수정합니다.

## 주의
- 이력은 앱이 실행되어 있는 동안(운영 시간 09~18시, 15분 주기)만 쌓입니다. 상시 수집이 필요하면 상시 실행되는 서버에서 띄우세요.
- Streamlit Community Cloud는 재시작 시 파일(news.db)이 초기화될 수 있습니다.
- 소스는 연합뉴스 RSS(`config.py`의 `FEED_URLS`)입니다. RSS는 최신 기사 일부만 담고 있어 15분마다 확인하는 방식에 맞습니다. 다른 연합뉴스 RSS를 추가하려면 `FEED_URLS`에 주소를 넣으세요.

## 텔레그램 채널 전송 (GitHub Actions)
`notify.py`가 새 기사를 모아 **메시지 1개**로 보냅니다(주요 기사는 🚨, 맨 위). 4,096자를 넘을 때만 나눠 보냅니다. `.github/workflows/news.yml`이
KST 09:00~18:00(09:00, 09:15 … 17:45, 18:00)에 15분마다 자동 실행합니다. 전송 이력은 `news_bot/sent.json`에 저장됩니다.

설정 순서:
1. 텔레그램 채널을 만들고, @BotFather `/newbot`으로 봇을 만든 뒤 봇을 채널 관리자(메시지 게시 권한)로 추가
2. 저장소 Settings → Secrets and variables → Actions 에 등록
   - `TELEGRAM_BOT_TOKEN`: BotFather가 준 토큰
   - `TELEGRAM_CHAT_ID`: 공개 채널 `@채널아이디` / 비공개 채널 `-100…` 숫자 ID
3. 기본 브랜치에 머지 후 Actions → weather-news-telegram → Run workflow 로 수동 테스트
   (Actions 스케줄은 기본 브랜치에서만 동작)

로컬 점검(전송 없이 출력만): `python news_bot/notify.py` (news_bot 폴더에서)
