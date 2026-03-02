# NFPC/NFTC 전수 제·개정 자동 모니터링 (신규 프로젝트)

국가법령정보센터 OPEN API를 이용해 **NFPC/NFTC 전체 조항(기준 목록)**의 최신 상태를 매일 자동 점검하고,
변경 이력을 GitHub에 누적하여 웹 대시보드에서 확인할 수 있는 프로젝트입니다.

## 핵심 기능
- NFPC/NFTC 기준 목록 전수 조회 (`standards_nfpc.json`, `standards_nftc.json`)
- 변경 감지(제·개정구분, 발령/시행일, 발령번호, 원문 링크, 응답 해시)
- 이력 누적 (`data.json`) 및 최신 스냅샷 저장 (`snapshot.json`)
- GitHub Pages 대시보드 제공 (`index.html`)
- 매일 오전 10시(KST) 자동 실행 (GitHub Actions)
- 변경 시 선택적으로 웹훅 알림 전송 (`ALERT_WEBHOOK_URL`)

---

## 1) 사전 준비
### OPEN API OC 발급
국가법령정보센터 OPEN API에서 OC를 발급받아야 합니다.

### GitHub Secrets 설정
Repository → Settings → Secrets and variables → Actions

필수:
- `LAWGO_OC`: 국가법령정보센터 OC 값

선택:
- `ALERT_WEBHOOK_URL`: Slack/Discord/사내 웹훅 URL (변경 발생 시 POST)

---

## 2) 실행 구조
- 자동 점검 스크립트: `scripts/check_updates.py`
- 기준 목록:
  - `standards_nfpc.json`
  - `standards_nftc.json`
- 결과물:
  - `snapshot.json` (최신 상태)
  - `data.json` (실행 이력)

---

## 3) GitHub Actions 스케줄
`.github/workflows/daily_check.yml`에서 설정됩니다.

- `cron: "0 1 * * *"` → UTC 01:00 = **KST 오전 10:00**

---

## 4) 로컬 테스트
```bash
export LAWGO_OC=발급받은_OC
python scripts/check_updates.py
