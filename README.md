# 🚒 NFPC/NFTC 자동 모니터링 대시보드

국가법령정보센터(법제처) Open API를 활용하여 소방청 **국가화재안전기준(NFPC) 및 국가화재안전기술기준(NFTC)**의 제·개정 상태를 매일 자동으로 추적하고 시각화하는 모니터링 시스템입니다.

🔗 **[대시보드 바로가기]([https://본인의깃허브아이디.github.io/레포지토리이름](https://shhan95.github.io/NFTC-NFPC-automated-review/))** *(👉 주소는 본인 깃허브 페이지 링크로 수정해 주세요!)*

---

## ✨ 주요 기능 (Key Features)

- **🕒 완전 자동화된 모니터링**
  - GitHub Actions를 통해 매일 오전 10시(KST) 파이썬 봇이 백그라운드에서 자동 실행됩니다.
  - 별도의 서버 유지보수 비용 없이 무료로 무인 운영됩니다.
- **💡 스마트 개정이유 브리핑 (New!)**
  - 단순한 변경 여부 감지를 넘어, 법령이 개정되었을 경우 **상세조회 API를 통해 '제·개정이유' 원문을 자동으로 추출**합니다.
  - 대시보드에 전문가용 브리핑 박스 형태로 요약본을 제공하여 즉각적인 내용 파악이 가능합니다.
- **📊 직관적인 웹 대시보드**
  - 각 법령의 현재 상태(FOUND / NOT_FOUND), 제·개정구분, 발령일, 시행일, 원문 링크를 한눈에 파악할 수 있습니다.
  - 검색 및 필터링 기능과 변경 이력(Log) 조회 기능을 지원합니다.
- **🔔 실시간 알림 시스템**
  - 변경 사항이 감지되면 즉시 Slack / Discord 등 지정된 Webhook으로 변경된 법령과 개정이유 요약본을 전송합니다.

## 🛠 기술 스택 (Tech Stack)

- **Backend / Automation:** `Python 3`, `GitHub Actions`
- **Frontend:** `HTML5`, `CSS3`, `Vanilla JavaScript`
- **Data Source:** [국가법령정보센터 Open API](https://open.law.go.kr/)
- **Database:** `JSON` 기반 정적 파일 저장 (`data.json`, `snapshot.json`)

## ⚙️ 설정 방법 (Setup)

본 저장소를 포크(Fork)하여 자신만의 모니터링 시스템을 구축할 수 있습니다.

1. **API 키 발급:** 국가법령정보센터 오픈 API 활용 신청 (대상: 행정규칙)
2. **GitHub Secrets 등록:** - `LAWGO_OC`: 법제처 오픈 API 인증키 (또는 가입 아이디)
   - `ALERT_WEBHOOK_URL`: 알림을 받을 Slack/Discord 웹훅 URL (선택 사항)
3. **권한 설정:** `Settings` > `Actions` > `General`에서 `Workflow permissions`를 **Read and write permissions**로 변경
4. **기준 목록 세팅:** `standards_nfpc.json`, `standards_nftc.json` 파일에 모니터링할 법령 리스트 작성

## 📁 프로젝트 구조

```text
📦 NFTC-NFPC-automated-review
 ┣ 📂 .github/workflows
 ┃ ┗ 📜 daily_check.yml       # 매일 봇을 실행하는 자동화 스케줄러
 ┣ 📂 scripts
 ┃ ┗ 📜 check_updates.py      # Open API 연동 및 데이터 수집 파이썬 로직
 ┣ 📜 index.html              # 대시보드 메인 화면
 ┣ 📜 app.js                  # 대시보드 화면 렌더링 및 기능 제어
 ┣ 📜 style.css               # 다크 테마 및 UI 디자인
 ┣ 📜 standards_nfpc.json     # NFPC 검색 기준 목록 (사용자 작성)
 ┣ 📜 standards_nftc.json     # NFTC 검색 기준 목록 (사용자 작성)
 ┣ 📜 snapshot.json           # 가장 최근 법령 상태를 기억하는 스냅샷 (자동 생성)
 ┗ 📜 data.json               # 일자별 변경 이력 및 통계 데이터 (자동 생성)
