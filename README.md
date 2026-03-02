# NFTC-NFPC-automated-review
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index 762f8be6d1fbc777cdedce478051904f27ce6ad4..4666d1cf686bb22418b039c87a874ac565dfa43b 100644
--- a/README.md
+++ b/README.md
@@ -1,28 +1,78 @@
-# NFPC/NFTC 전수 자동검토 (GitHub Pages + GitHub Actions)
+# NFPC/NFTC 전수 제·개정 자동 모니터링 (신규 프로젝트)
 
-## 구성
-- GitHub Pages: `index.html`이 `data.json`, `snapshot.json`, `standards_*.json`을 읽어 대시보드 표시
-- GitHub Actions: 매일 07:00(KST) 자동 실행 → 법제처 OPEN API로 전수 조회 → 변경 여부를 `data.json`에 누적 기록
+국가법령정보센터 OPEN API를 이용해 **NFPC/NFTC 전체 조항(기준 목록)**의 최신 상태를 매일 자동 점검하고,
+변경 이력을 GitHub에 누적하여 웹 대시보드에서 확인할 수 있는 프로젝트입니다.
 
-## 1) 법제처 OPEN API OC 값 준비
-- 법제처 국가법령정보 공동활용(OPEN API)에서 발급/등록한 **OC**가 필요합니다.
-- OC는 보통 이메일의 ID(예: g4c@korea.kr → g4c) 형태로 안내됩니다.
+## 핵심 기능
+- NFPC/NFTC 기준 목록 전수 조회 (`standards_nfpc.json`, `standards_nftc.json`)
+- 변경 감지(제·개정구분, 발령/시행일, 발령번호, 원문 링크, 응답 해시)
+- 이력 누적 (`data.json`) 및 최신 스냅샷 저장 (`snapshot.json`)
+- GitHub Pages 대시보드 제공 (`index.html`)
+- 매일 오전 10시(KST) 자동 실행 (GitHub Actions)
+- 변경 시 선택적으로 웹훅 알림 전송 (`ALERT_WEBHOOK_URL`)
 
-## 2) GitHub Secret 설정
-Repo → Settings → Secrets and variables → Actions → New repository secret
-- Name: `LAWGO_OC`
-- Value: (본인의 OC 값)
+---
 
-## 3) 배포
-Repo → Settings → Pages
-- Source: `Deploy from a branch`
+## 1) 사전 준비
+### OPEN API OC 발급
+국가법령정보센터 OPEN API에서 OC를 발급받아야 합니다.
+
+### GitHub Secrets 설정
+Repository → Settings → Secrets and variables → Actions
+
+필수:
+- `LAWGO_OC`: 국가법령정보센터 OC 값
+
+선택:
+- `ALERT_WEBHOOK_URL`: Slack/Discord/사내 웹훅 URL (변경 발생 시 POST)
+
+---
+
+## 2) 실행 구조
+- 자동 점검 스크립트: `scripts/check_updates.py`
+- 기준 목록:
+  - `standards_nfpc.json`
+  - `standards_nftc.json`
+- 결과물:
+  - `snapshot.json` (최신 상태)
+  - `data.json` (실행 이력)
+
+---
+
+## 3) GitHub Actions 스케줄
+`.github/workflows/daily_check.yml`에서 설정됩니다.
+
+- `cron: "0 1 * * *"` → UTC 01:00 = **KST 오전 10:00**
+
+---
+
+## 4) 로컬 테스트
+```bash
+export LAWGO_OC=발급받은_OC
+python scripts/check_updates.py
+```
+
+검증 명령:
+```bash
+python -m py_compile scripts/check_updates.py
+node --check app.js
+```
+
+---
+
+## 5) GitHub Pages 배포
+Repository → Settings → Pages
+- Source: Deploy from a branch
 - Branch: `main` / root
-저장 후 1~2분 뒤 `https://<계정>.github.io/<repo>/`로 접속
 
-## 4) 수동 테스트
-Actions 탭 → `NFPC NFTC Daily Check` → Run workflow
-완료 후 `data.json`/`snapshot.json` 커밋이 생성되면 정상.
+페이지에서 다음 확인 가능:
+- 마지막 점검 시각
+- NFPC/NFTC 항목별 최신 상태
+- 일자별 변경 이력
+- 항목 상세 메타데이터
+
+---
 
-## 주의
-- 본 자동검토는 기본적으로 ‘발령/시행/발령번호/제개정구분 + 본문 해시’ 변경 감지입니다.
-- 조문·별표 ‘신구대비 표’는 별도(부가) API 신청 또는 추가 파싱 로직이 필요할 수 있습니다.
+## 참고
+- OPEN API 응답 포맷 차이를 고려해 스키마 유연 파싱을 적용했습니다.
+- 특정 항목이 검색되지 않을 경우 `NOT_FOUND`로 기록되며, 다음 실행 시 재평가됩니다.
 
EOF
)
