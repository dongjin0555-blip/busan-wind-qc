# 부산·울산·경남 기상·재해 뉴스 대시보드

기상 이슈, 화재·재해·사고, 교통 영향 뉴스를 연합뉴스 RSS로 수집해 Streamlit으로 보여줍니다.

## 실행 (API 키 불필요)
```bash
pip install -r news_bot/requirements.txt
streamlit run news_bot/app.py
```
브라우저에서 http://localhost:8501 — 연합뉴스 RSS를 사용하므로 계정/키가 필요 없습니다.

## 기능
- 분류 규칙 (`config.py`에서 그룹별로 관리)
  - A 기상 요인(`CAUSE`) / B 재해·피해(`DAMAGE`) / C 기상자료 확인이 필요할 수 있는 사고 유형(`NEEDS_DATA`) / 제외어(`EXCLUDE`)
  - 🚨 **기상 원인**: A와 (B 또는 C)가 함께 있음 (예: 강풍에 외벽 붕괴, 안개로 다중 추돌)
  - 🚨 **기상특보**: 특보·주의보·경보 발효/해제 기사
  - ▪️ **자료 확인**: C 유형 사고만 있고 원인은 없음 (예: 어선 전복, 산불) → 관측 자료 확인 후보
  - A만 있는 일반 날씨 기사, 제외어(훈련·화재보험·맛집 등) 기사는 받지 않음
- 제외된 기사: 지역은 맞지만 탈락한 기사를 대시보드 하단 "제외된 기사"에서 확인 → 키워드 튜닝에 활용
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

## HTML 대시보드 (news/index.html)
서버 없이 정적 파일로 동작하는 대시보드입니다. 수집기(`notify.py`)가 15분마다 `news/data.json`에
기사를 14일치 누적 저장하고(제외된 기사는 2일치), `news/index.html`이 그 파일을 읽어 그립니다.
- 주요 기사, 건수 요약, 시간대/일별 차트, 키워드별 차트(표로 보기 전환), 전체 목록, CSV 다운로드, 제외된 기사
- 필터: 기간(오늘/24시간/3일/7일/14일), 지역, 분류, 키워드, 제목 검색
- 화면을 열어 두면 5분마다 데이터를 다시 읽음, 라이트/다크 자동 + 수동 전환
- GitHub Pages로 공개: 저장소 Settings → Pages → Branch `main` / `(root)` 로 설정하면
  `https://<계정>.github.io/busan-wind-qc/news/` 에서 열림
- 로컬 확인: `python -m http.server` 실행 후 `http://localhost:8000/news/`
