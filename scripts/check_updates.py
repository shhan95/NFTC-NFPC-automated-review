import hashlib
import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

KST = timezone(timedelta(hours=9))
NOW = lambda: datetime.now(KST)
TODAY = NOW().strftime("%Y-%m-%d")

LAWGO_OC = os.getenv("LAWGO_OC", "").strip()
if not LAWGO_OC:
    raise SystemExit("ENV LAWGO_OC is empty. Set GitHub Secret 'LAWGO_OC'.")

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()

# 검색 API와 상세조회 API 주소 분리
LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"

TIMEOUT = int(os.getenv("LAWGO_TIMEOUT", "12"))
MAX_RETRIES = int(os.getenv("LAWGO_MAX_RETRIES", "3"))
REQUEST_GAP = float(os.getenv("LAWGO_REQUEST_GAP", "1.5"))


def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def normalize_date(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}.{s[4:6]}.{s[6:8]}"
    return s


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "")


def backoff(attempt: int) -> None:
    base = 0.5 * (2 ** (attempt - 1))
    time.sleep(base + random.random() * 0.35)


def http_get_json(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    query = urllib.parse.urlencode(params, doseq=False, safe="")
    req_url = f"{url}?{query}"

    headers = {
        "Accept": "application/json,*/*;q=0.8",
        "User-Agent": "NFPC-NFTC-Monitor/2.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(req_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if not raw:
                    raise ValueError("empty response")
                return json.loads(raw)
        except Exception:
            if attempt >= MAX_RETRIES:
                return None
            backoff(attempt)
    return None


def to_dict_list(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    top = payload.get("AdmRulSearch") or payload.get("admrulSearch")
    if isinstance(top, dict):
        candidates.extend(to_dict_list(top.get("admrul")))

    for key in ("admrul", "items", "results", "law"):
        candidates.extend(to_dict_list(payload.get(key)))

    uniq: List[Dict[str, Any]] = []
    seen = set()
    for item in candidates:
        sig = sha256_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(item)
    return uniq


def pick_best_item(items: List[Dict[str, Any]], std: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not items:
        return None

    std_title = normalize_text(std.get("title"))
    std_org = normalize_text(std.get("orgName"))

    def score(item: Dict[str, Any]) -> int:
        title = normalize_text(item.get("법령명한글") or item.get("법령명") or item.get("행정규칙명"))
        org = normalize_text(item.get("소관부처") or item.get("소관부처명"))
        rev = str(item.get("제개정구분명") or item.get("제개정구분") or "")
        s = 0
        if title == std_title:
            s += 10
        elif std_title and std_title in title:
            s += 6
        if std_org and std_org in org:
            s += 3
        if rev in ("개정", "제정", "전부개정", "일부개정"):
            s += 1
        return s

    return sorted(items, key=score, reverse=True)[0]


def build_snapshot(std: Dict[str, Any], item: Optional[Dict[str, Any]], error: str = "") -> Dict[str, Any]:
    now = NOW().isoformat(timespec="seconds")
    if error or not item:
        return {
            "code": std.get("code"),
            "title": std.get("title"),
            "status": "ERROR" if error else "NOT_FOUND",
            "checkedAt": now,
            "error": error,
            "seq": "",
            "noticeNo": "",
            "announceDate": "",
            "effectiveDate": "",
            "revisionType": "",
            "htmlUrl": "",
            "sourceHash": "",
        }

    source_hash = sha256_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
    html_url = item.get("법령상세링크") or item.get("상세링크") or ""
    
    # 일련번호(seq) 추출 추가
    seq = str(item.get("행정규칙일련번호") or item.get("법령일련번호") or "")

    return {
        "code": std.get("code"),
        "title": std.get("title"),
        "status": "FOUND",
        "checkedAt": now,
        "error": "",
        "seq": seq,
        "noticeNo": str(item.get("공포번호") or item.get("발령번호") or ""),
        "announceDate": normalize_date(item.get("공포일자") or item.get("발령일자")),
        "effectiveDate": normalize_date(item.get("시행일자")),
        "revisionType": str(item.get("제개정구분명") or item.get("제개정구분") or ""),
        "htmlUrl": str(html_url),
        "sourceHash": source_hash,
    }


def fetch_standard(std: Dict[str, Any]) -> Dict[str, Any]:
    query = (std.get("query") or std.get("title") or "").strip()
    if not query:
        return build_snapshot(std, None, error="empty query")

    params = {
        "OC": LAWGO_OC,
        "target": "admrul",
        "type": "JSON",
        "query": query,
        "display": "30",
    }
    payload = http_get_json(LAW_SEARCH_URL, params)
    if payload is None:
        return build_snapshot(std, None, error="api request failed")

    items = extract_items(payload)
    best = pick_best_item(items, std)
    return build_snapshot(std, best)


# 🌟 새로 추가된 핵심 기능: 변경된 법령의 개정이유를 상세조회 API에서 가져옵니다!
def fetch_revision_reason(seq: str) -> str:
    if not seq:
        return ""
    
    params = {
        "OC": LAWGO_OC,
        "target": "admrul",
        "type": "JSON",
        "ID": seq
    }
    
    payload = http_get_json(LAW_SERVICE_URL, params)
    if not payload:
        return "상세 내용을 불러오지 못했습니다."
    
    # 상세 데이터에서 '제개정이유' 파싱
    try:
        # 법제처 API 구조에 따라 'AdmRul' -> '제개정이유' 텍스트를 추출
        adm_rul = payload.get("AdmRul", {})
        reason = adm_rul.get("제개정이유", "")
        # 만약 내용이 없거나 태그 찌꺼기가 섞여 있다면 기본 텍스트 반환
        if reason:
            # 간단한 HTML 태그 제거나 공백 정리 (필요시)
            reason = reason.replace("<![CDATA[", "").replace("]]>", "").strip()
            return reason
    except Exception:
        pass
        
    return "별도의 개정이유가 제공되지 않았습니다. 상세 링크를 확인해주세요."


def diff_changed(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> Tuple[bool, List[str]]:
    keys = ["status", "noticeNo", "announceDate", "effectiveDate", "revisionType", "htmlUrl", "sourceHash", "error"]
    if not prev:
        return True, ["new"]

    changed_fields = [k for k in keys if (prev.get(k) or "") != (cur.get(k) or "")]
    return (len(changed_fields) > 0), changed_fields


def process_scope(scope: str, standards_file: str, prev_scope: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, int]]:
    standards = load_json(standards_file, {"items": []}).get("items", [])
    latest: Dict[str, Any] = {}
    changes: List[Dict[str, Any]] = []
    stats = {"total": 0, "found": 0, "notFound": 0, "error": 0, "changed": 0}

    for std in standards:
        code = std.get("code")
        if not code:
            continue

        stats["total"] += 1
        cur = fetch_standard(std)
        prev = prev_scope.get(code)

        if cur["status"] == "FOUND":
            stats["found"] += 1
        elif cur["status"] == "NOT_FOUND":
            stats["notFound"] += 1
        else:
            stats["error"] += 1

        changed, changed_fields = diff_changed(prev, cur)
        if changed:
            stats["changed"] += 1
            
            # 🌟 변경이 감지되었을 때만 상세조회를 돌려서 개정이유를 가져옵니다.
            revision_reason = ""
            if cur.get("seq") and cur.get("status") == "FOUND":
                revision_reason = fetch_revision_reason(cur.get("seq"))
                time.sleep(REQUEST_GAP)  # 상세조회 후에도 서버 과부하 방지 휴식
            
            changes.append(
                {
                    "scope": scope,
                    "code": code,
                    "title": std.get("title", ""),
                    "status": cur.get("status", ""),
                    "revisionType": cur.get("revisionType", ""),
                    "announceDate": cur.get("announceDate", ""),
                    "effectiveDate": cur.get("effectiveDate", ""),
                    "changedFields": changed_fields,
                    "reason": revision_reason,  # 데이터에 이유 추가!
                    "url": cur.get("htmlUrl", "")
                }
            )

        latest[code] = cur
        time.sleep(REQUEST_GAP)

    return latest, changes, stats


def post_webhook(message: str) -> None:
    if not ALERT_WEBHOOK_URL:
        return
    payload = json.dumps({"text": message}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        ALERT_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=8).read()
    except Exception:
        pass


def main() -> None:
    data = load_json("data.json", {"lastRun": None, "records": []})
    snapshot = load_json("snapshot.json", {"nfpc": {}, "nftc": {}})

    nfpc_latest, nfpc_changes, nfpc_stats = process_scope("NFPC", "standards_nfpc.json", snapshot.get("nfpc", {}))
    nftc_latest, nftc_changes, nftc_stats = process_scope("NFTC", "standards_nftc.json", snapshot.get("nftc", {}))

    all_changes = nfpc_changes + nftc_changes
    result = "변경 있음" if all_changes else "변경 없음"

    summary = (
        f"NFPC {nfpc_stats['changed']}건 변경 | "
        f"NFTC {nftc_stats['changed']}건 변경"
    )

    # 알림 발송용 상세 텍스트 조립
    detail_msg = ""
    for c in all_changes:
        detail_msg += f"\n[{c['scope']}] {c['title']} ({c['revisionType']})\n"
        if c.get("reason"):
            detail_msg += f"💡 개정이유: {c['reason'][:200]}...\n" # 너무 길면 잘라서 보여줌
        detail_msg += f"🔗 링크: {c['url']}\n"

    record = {
        "date": TODAY,
        "checkedAt": NOW().isoformat(timespec="seconds"),
        "scope": "NFPC/NFTC",
        "result": result,
        "summary": summary,
        "stats": {"nfpc": nfpc_stats, "nftc": nftc_stats},
        "changes": all_changes,
    }

    records = data.get("records", [])
    if records and records[0].get("date") == TODAY:
        records[0] = record
    else:
        records.insert(0, record)

    data["lastRun"] = NOW().isoformat(timespec="seconds")
    data["records"] = records[:365]

    snapshot["nfpc"] = nfpc_latest
    snapshot["nftc"] = nftc_latest

    save_json("data.json", data)
    save_json("snapshot.json", snapshot)

    short = f"[{TODAY}] {result} - {summary}"
    print(short)
    if detail_msg:
        print(detail_msg)

    if all_changes:
        post_webhook(f"{short}\n{detail_msg}")


if __name__ == "__main__":
    main()
