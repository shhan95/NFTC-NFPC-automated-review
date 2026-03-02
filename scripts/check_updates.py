 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/scripts/check_updates.py b/scripts/check_updates.py
index fb65a9fffd4fd32ecc71990e346d47a4885b6360..b190677542646867bb80e8edf4627cf1573e2d9d 100644
--- a/scripts/check_updates.py
+++ b/scripts/check_updates.py
@@ -1,384 +1,422 @@
-import os, json, hashlib, urllib.parse, time, random
-from datetime import datetime, timezone, timedelta
-from typing import Any, Dict, Tuple, Optional
-
-import requests
+import hashlib
+import json
+import os
+import random
+import time
+import urllib.error
+import urllib.parse
+import urllib.request
+from datetime import datetime, timedelta, timezone
+from typing import Any, Dict, List, Optional, Tuple
 
 
 # =====================
 # Config
 # =====================
 KST = timezone(timedelta(hours=9))
 TODAY = datetime.now(KST).strftime("%Y-%m-%d")
 
 LAWGO_OC = os.getenv("LAWGO_OC", "").strip()
 if not LAWGO_OC:
-    raise SystemExit("ENV LAWGO_OC is empty. Set GitHub Secret 'LAWGO_OC' to your 법제처 OPEN API OC value (email id).")
+    raise SystemExit(
+        "ENV LAWGO_OC is empty. Set GitHub Secret 'LAWGO_OC' to your 법제처 OPEN API OC value (email id)."
+    )
 
-# ✅ https 고정
 LAW_SEARCH = "https://www.law.go.kr/DRF/lawSearch.do"
 LAW_SERVICE = "https://www.law.go.kr/DRF/lawService.do"
 
-TIMEOUT = 30
-MAX_RETRIES = 4
+TIMEOUT = int(os.getenv("LAWGO_TIMEOUT", "15"))
+MAX_RETRIES = int(os.getenv("LAWGO_MAX_RETRIES", "3"))
 
 
 # =====================
 # Helpers (file I/O)
 # =====================
 def load(path: str, default: Any) -> Any:
     try:
         with open(path, "r", encoding="utf-8") as f:
             return json.load(f)
     except FileNotFoundError:
         return default
 
+
 def save(path: str, obj: Any) -> None:
     with open(path, "w", encoding="utf-8") as f:
         json.dump(obj, f, ensure_ascii=False, indent=2)
 
+
 def ymd_int_to_dot(v: Any) -> Any:
     if v is None:
         return None
     s = str(v).strip()
     if not s.isdigit() or len(s) != 8:
         return s
     return f"{s[0:4]}.{s[4:6]}.{s[6:8]}"
 
-def sha256_text(t: str) -> str:
-    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()
+
+def sha256_text(text: str) -> str:
+    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
 
 
 # =====================
 # HTTP (robust)
 # =====================
+def _backoff(attempt: int) -> None:
+    # 0.5s, 1.0s, 2.0s ... + jitter
+    base = 0.5 * (2 ** (attempt - 1))
+    time.sleep(base + random.random() * 0.4)
+
+
 def _request_json(url: str, params: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
-    """
-    Returns: (json_payload, error_info)
-      - json_payload: parsed dict if success
-      - error_info: dict with debug fields if failed (no secret exposure)
-    """
-    session = requests.Session()
-    last_err = None
+    last_err: Optional[Dict[str, Any]] = None
+    headers = {
+        "Accept": "application/json,*/*;q=0.8",
+        "User-Agent": "NFPC-NFTC-Automated-Review-System/1.0",
+    }
+
+    query = urllib.parse.urlencode(params, doseq=False, safe="")
+    request_url = f"{url}?{query}"
 
     for attempt in range(1, MAX_RETRIES + 1):
+        req = urllib.request.Request(request_url, headers=headers, method="GET")
+
         try:
-            r = session.get(url, params=params, timeout=TIMEOUT, allow_redirects=True)
-            ct = (r.headers.get("Content-Type") or "").lower()
-            text = r.text or ""
+            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
+                status = getattr(response, "status", response.getcode())
+                content_type = (response.headers.get("Content-Type") or "").lower()
+                text = response.read().decode("utf-8", errors="replace")
+
             head = text[:200].replace("\n", " ")
 
-            # status not ok
-            if r.status_code != 200:
+            if status != 200:
                 last_err = {
                     "kind": "http_error",
-                    "status": r.status_code,
-                    "contentType": ct,
+                    "status": status,
+                    "contentType": content_type,
                     "head": head,
                     "url": url,
                 }
-                # 429/5xx는 재시도 가치 큼
-                if r.status_code in (429, 500, 502, 503, 504):
+                if status in (429, 500, 502, 503, 504):
                     _backoff(attempt)
                     continue
                 return None, last_err
 
-            # content type not json (HTML/empty/blocked)
-            if "json" not in ct:
-                # 빈 응답도 여기로 들어옴
+            if "json" not in content_type:
                 last_err = {
                     "kind": "not_json",
-                    "status": r.status_code,
-                    "contentType": ct,
+                    "status": status,
+                    "contentType": content_type,
                     "head": head,
                     "url": url,
                 }
-                # 일시 오류 가능 → 재시도
                 _backoff(attempt)
                 continue
 
-            # try parse json
             try:
-                return r.json(), None
-            except Exception as e:
+                payload = json.loads(text)
+            except Exception as e:  # noqa: BLE001
                 last_err = {
                     "kind": "json_parse_fail",
-                    "status": r.status_code,
-                    "contentType": ct,
+                    "status": status,
+                    "contentType": content_type,
                     "head": head,
                     "url": url,
                     "error": str(e),
                 }
                 _backoff(attempt)
                 continue
 
-        except requests.RequestException as e:
+            if not isinstance(payload, dict):
+                last_err = {
+                    "kind": "json_type_error",
+                    "status": status,
+                    "contentType": content_type,
+                    "head": head,
+                    "url": url,
+                }
+                _backoff(attempt)
+                continue
+
+            return payload, None
+
+        except urllib.error.HTTPError as e:
+            body = ""
+            try:
+                body = e.read().decode("utf-8", errors="replace")
+            except Exception:
+                body = ""
+
+            last_err = {
+                "kind": "http_error",
+                "status": e.code,
+                "contentType": (e.headers.get("Content-Type") or "").lower() if e.headers else "",
+                "head": body[:200].replace("\n", " "),
+                "url": url,
+                "error": str(e),
+            }
+            if e.code in (429, 500, 502, 503, 504):
+                _backoff(attempt)
+                continue
+            return None, last_err
+
+        except (urllib.error.URLError, TimeoutError, OSError) as e:
             last_err = {
                 "kind": "request_exception",
                 "url": url,
                 "error": str(e),
             }
             _backoff(attempt)
             continue
 
     return None, last_err
 
-def _backoff(attempt: int) -> None:
-    # 0.6s, 1.2s, 2.4s... + jitter
-    base = 0.6 * (2 ** (attempt - 1))
-    time.sleep(base + random.random() * 0.4)
-
 
 # =====================
 # Law.go API wrappers
 # =====================
 def lawgo_search(query: str, knd: int = 3, display: int = 20) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
     params = {
         "OC": LAWGO_OC,
         "target": "admrul",
         "type": "JSON",
         "query": query,
         "knd": str(knd),
         "display": str(display),
         "sort": "ddes",
     }
-print("STATUS", r.status_code)
-print("CT", r.headers.get("Content-Type"))
-print("HEAD", (r.text or "")[:200].replace("\n", " "))
     return _request_json(LAW_SEARCH, params)
 
+
 def lawgo_detail(admrul_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
     params = {
         "OC": LAWGO_OC,
         "target": "admrul",
         "type": "JSON",
         "ID": str(admrul_id),
     }
     return _request_json(LAW_SERVICE, params)
 
 
 # =====================
-# Picking / parsing
+# Parsing / selection
 # =====================
-def pick_best_item(items, org_name="소방청"):
-    best = None
+def pick_best_item(items: List[Dict[str, Any]], org_name: str = "소방청") -> Optional[Dict[str, Any]]:
+    best: Optional[Dict[str, Any]] = None
     best_score = -1
+
     for it in items or []:
         org = (it.get("소관부처명") or it.get("소관부처") or "")
         kind = (it.get("행정규칙종류") or "")
+
         score = 0
         if org_name and org_name in org:
             score += 100
         if "고시" in kind:
             score += 20
         if it.get("발령일자"):
             score += 1
+
         if score > best_score:
-            best, best_score = it, score
+            best = it
+            best_score = score
+
     return best
 
-def _extract_items(search_json: Dict[str, Any]) -> list:
-    for k in ("admrul", "Admrul", "admruls"):
-        if k in search_json:
-            return search_json.get(k) or []
-    if "행정규칙" in search_json and isinstance(search_json["행정규칙"], list):
+
+def _extract_items(search_json: Dict[str, Any]) -> List[Dict[str, Any]]:
+    for key in ("admrul", "Admrul", "admruls"):
+        value = search_json.get(key)
+        if isinstance(value, list):
+            return value
+
+    if isinstance(search_json.get("행정규칙"), list):
         return search_json["행정규칙"]
+
     return []
 
+
 def _extract_payload(detail_json: Dict[str, Any]) -> Dict[str, Any]:
-    # 상세 구조 다양성 대응
-    if isinstance(detail_json.get("행정규칙"), dict):
-        return detail_json["행정규칙"]
-    if isinstance(detail_json.get("admrul"), dict):
-        return detail_json["admrul"]
+    for key in ("행정규칙", "admrul"):
+        value = detail_json.get(key)
+        if isinstance(value, dict):
+            return value
     return detail_json
 
 
+def _admrul_html_url(adm_id: Any, best: Dict[str, Any]) -> str:
+    html_url = best.get("행정규칙상세링크") or best.get("상세링크") or ""
+    if html_url:
+        return str(html_url)
+
+    encoded_id = urllib.parse.quote(str(adm_id))
+    encoded_oc = urllib.parse.quote(LAWGO_OC)
+    return f"{LAW_SERVICE}?OC={encoded_oc}&target=admrul&ID={encoded_id}&type=HTML"
+
+
 # =====================
 # Snapshot builder
 # =====================
-def build_snapshot_entry(std_item: Dict[str, Any], tab_key: str, prev_entry: Dict[str, Any]) -> Dict[str, Any]:
+def build_snapshot_entry(std_item: Dict[str, Any], prev_entry: Dict[str, Any]) -> Dict[str, Any]:
     query = std_item.get("query") or std_item.get("title") or std_item.get("code")
     knd = int(std_item.get("knd", 3))
     org_name = std_item.get("orgName", "소방청")
 
-    # 1) search
-    sj, err = lawgo_search(query, knd=knd)
-    if err:
+    search_json, search_err = lawgo_search(query=query, knd=knd)
+    if search_err:
         return {
             **(prev_entry or {}),
             "code": std_item.get("code"),
             "title": std_item.get("title"),
             "checkedAt": TODAY,
-            "error": {
-                "where": "search",
-                **err,
-                "query": query,
-            },
+            "error": {"where": "search", **search_err, "query": query},
         }
 
-    items = _extract_items(sj or {})
+    items = _extract_items(search_json or {})
     best = pick_best_item(items, org_name=org_name)
     if not best:
         return {
             **(prev_entry or {}),
             "code": std_item.get("code"),
             "title": std_item.get("title"),
             "checkedAt": TODAY,
             "error": {"where": "search", "kind": "no_results", "query": query},
         }
 
     adm_id = best.get("행정규칙일련번호") or best.get("일련번호") or best.get("id") or best.get("ID")
     if not adm_id:
         return {
             **(prev_entry or {}),
             "code": std_item.get("code"),
             "title": std_item.get("title"),
             "checkedAt": TODAY,
             "error": {"where": "search", "kind": "id_missing", "query": query},
         }
 
-    # 2) detail
-    dj, derr = lawgo_detail(str(adm_id))
-    if derr:
+    detail_json, detail_err = lawgo_detail(str(adm_id))
+    if detail_err:
         return {
             **(prev_entry or {}),
             "code": std_item.get("code"),
             "title": std_item.get("title"),
             "checkedAt": TODAY,
             "lawgoId": str(adm_id),
-            "error": {"where": "detail", **derr},
+            "error": {"where": "detail", **detail_err},
         }
 
-    payload = _extract_payload(dj or {})
-
-    notice_no = payload.get("발령번호")
-    announce = ymd_int_to_dot(payload.get("발령일자"))
-    effective = ymd_int_to_dot(payload.get("시행일자"))
-    rev = payload.get("제개정구분명")
-    org = payload.get("소관부처명")
-    name = payload.get("행정규칙명") or std_item.get("title")
-
-    body_hash = sha256_text(payload.get("조문내용") or "")
-    add_hash = sha256_text((payload.get("부칙내용") or "") + (payload.get("별표내용") or ""))
-
-    html_url = best.get("행정규칙상세링크") or best.get("상세링크") or ""
-    if not html_url:
-        html_url = f"{LAW_SERVICE}?OC={urllib.parse.quote(LAWGO_OC)}&target=admrul&ID={adm_id}&type=HTML"
+    payload = _extract_payload(detail_json or {})
 
     return {
         "code": std_item.get("code"),
         "title": std_item.get("title"),
         "checkedAt": TODAY,
         "lawgoId": str(adm_id),
-        "noticeNo": notice_no,
-        "announceDate": announce,
-        "effectiveDate": effective,
-        "revisionType": rev,
-        "orgName": org,
-        "ruleName": name,
-        "htmlUrl": html_url,
-        "bodyHash": body_hash,
-        "suppHash": add_hash,
+        "noticeNo": payload.get("발령번호"),
+        "announceDate": ymd_int_to_dot(payload.get("발령일자")),
+        "effectiveDate": ymd_int_to_dot(payload.get("시행일자")),
+        "revisionType": payload.get("제개정구분명"),
+        "orgName": payload.get("소관부처명"),
+        "ruleName": payload.get("행정규칙명") or std_item.get("title"),
+        "htmlUrl": _admrul_html_url(adm_id, best),
+        "bodyHash": sha256_text(payload.get("조문내용") or ""),
+        "suppHash": sha256_text((payload.get("부칙내용") or "") + (payload.get("별표내용") or "")),
     }
 
-def detect_change(prev: Dict[str, Any], cur: Dict[str, Any]) -> Tuple[bool, list]:
+
+def detect_change(prev: Dict[str, Any], cur: Dict[str, Any]) -> Tuple[bool, List[str]]:
     if not prev:
         return False, []
+
     if prev.get("error") or cur.get("error"):
-        # 에러 상태 변화도 기록 가치가 있음
         if (prev.get("error") or "") != (cur.get("error") or ""):
             return True, ["error"]
         return False, []
+
     keys = ["noticeNo", "announceDate", "effectiveDate", "revisionType", "bodyHash", "suppHash"]
-    diffs = [k for k in keys if (prev.get(k) or "") != (cur.get(k) or "")]
-    return (len(diffs) > 0), diffs
+    diffs = [key for key in keys if (prev.get(key) or "") != (cur.get(key) or "")]
+    return len(diffs) > 0, diffs
 
 
 # =====================
 # Main
 # =====================
-def main():
+def main() -> None:
     nfpc = load("standards_nfpc.json", {"items": []})
     nftc = load("standards_nftc.json", {"items": []})
     snap = load("snapshot.json", {"nfpc": {}, "nftc": {}})
     data = load("data.json", {"lastRun": None, "records": []})
 
-    changes = []
-    errors = []
+    changes: List[Dict[str, Any]] = []
+    errors: List[Dict[str, Any]] = []
 
     for tab_key, std in (("nfpc", nfpc), ("nftc", nftc)):
         for item in std.get("items", []):
             code = item.get("code")
             if not code:
                 continue
 
             prev = (snap.get(tab_key, {}) or {}).get(code, {})
-            cur = build_snapshot_entry(item, tab_key, prev)
+            cur = build_snapshot_entry(item, prev)
             snap.setdefault(tab_key, {})[code] = cur
 
-            # 에러 누적
             if cur.get("error"):
-                errors.append({
-                    "code": code,
-                    "title": item.get("title"),
-                    "where": cur["error"].get("where"),
-                    "kind": cur["error"].get("kind"),
-                    "status": cur["error"].get("status"),
-                    "contentType": cur["error"].get("contentType"),
-                    "head": cur["error"].get("head"),
-                    "url": cur["error"].get("url"),
-                })
+                errors.append(
+                    {
+                        "code": code,
+                        "title": item.get("title"),
+                        "where": cur["error"].get("where"),
+                        "kind": cur["error"].get("kind"),
+                        "status": cur["error"].get("status"),
+                        "contentType": cur["error"].get("contentType"),
+                        "head": cur["error"].get("head"),
+                        "url": cur["error"].get("url"),
+                    }
+                )
 
             changed, diff_keys = detect_change(prev, cur)
             if changed and not cur.get("error"):
-                changes.append({
-                    "code": code,
-                    "title": item.get("title"),
-                    "noticeNo": cur.get("noticeNo"),
-                    "announceDate": cur.get("announceDate"),
-                    "effectiveDate": cur.get("effectiveDate"),
-                    "reason": f"자동 감지: 메타/본문 해시 변경({', '.join(diff_keys)})",
-                    "diff": [],
-                    "supplementary": "부칙/경과규정은 원문 확인",
-                    "impact": [
-                        "설계: 시행일 기준 적용(도서·시방서에 적용기준 명시)",
-                        "시공: 자재/설비 선정 시 개정기준 충족 여부 확인",
-                        "유지관리: 점검대장에 적용기준/이력 기록",
-                    ],
-                    "refs": [{"label": "법제처(원문/DRF)", "url": cur.get("htmlUrl", "")}],
-                })
+                changes.append(
+                    {
+                        "code": code,
+                        "title": item.get("title"),
+                        "noticeNo": cur.get("noticeNo"),
+                        "announceDate": cur.get("announceDate"),
+                        "effectiveDate": cur.get("effectiveDate"),
+                        "reason": f"자동 감지: 메타/본문 해시 변경({', '.join(diff_keys)})",
+                        "diff": [],
+                        "supplementary": "부칙/경과규정은 원문 확인",
+                        "impact": [
+                            "설계: 시행일 기준 적용(도서·시방서에 적용기준 명시)",
+                            "시공: 자재/설비 선정 시 개정기준 충족 여부 확인",
+                            "유지관리: 점검대장에 적용기준/이력 기록",
+                        ],
+                        "refs": [{"label": "법제처(원문/DRF)", "url": cur.get("htmlUrl", "")}],
+                    }
+                )
 
     data["lastRun"] = TODAY
 
-    if changes:
-        result = "변경 있음"
-        summary = f"자동 감지: {len(changes)}건 변경(원문 확인 권장)"
-    else:
-        result = "변경 없음"
-        summary = "전일 대비 변경 감지 없음"
+    result = "변경 있음" if changes else "변경 없음"
+    summary = f"자동 감지: {len(changes)}건 변경(원문 확인 권장)" if changes else "전일 대비 변경 감지 없음"
 
-    # 에러가 있어도 워크플로는 “성공”으로 두고, 기록만 남김
     rec = {
         "id": TODAY,
         "date": TODAY,
         "scope": "NFPC / NFTC (법제처 OPEN API: 행정규칙)",
         "result": result,
         "summary": summary,
         "changes": changes,
         "errors": errors,
         "refs": [],
     }
 
-    # 같은 날짜 있으면 교체
     data["records"] = [r for r in data.get("records", []) if r.get("date") != TODAY]
     data["records"].insert(0, rec)
 
     save("snapshot.json", snap)
     save("data.json", data)
 
-    # 에러가 많아도 exit 0 (운영 지속)
     print(f"Done. changes={len(changes)} errors={len(errors)} date={TODAY}")
 
+
 if __name__ == "__main__":
     main()
 
EOF
)
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

LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
TIMEOUT = int(os.getenv("LAWGO_TIMEOUT", "12"))
MAX_RETRIES = int(os.getenv("LAWGO_MAX_RETRIES", "3"))
REQUEST_GAP = float(os.getenv("LAWGO_REQUEST_GAP", "0.2"))


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
        if std_org and std_org and std_org in org:
            s += 3
        if rev in ("개정", "제정", "전부개정", "일부개정"):
            s += 1
        return s

    return sorted(items, key=score, reverse=True)[0]


def build_snapshot(std: Dict[str, Any], item: Optional[Dict[str, Any]], error: str = "") -> Dict[str, Any]:
    now = NOW().isoformat(timespec="seconds")

    if error:
        return {
            "code": std.get("code"),
            "title": std.get("title"),
            "status": "ERROR",
            "checkedAt": now,
            "error": error,
            "noticeNo": "",
            "announceDate": "",
            "effectiveDate": "",
            "revisionType": "",
            "htmlUrl": "",
            "sourceHash": "",
        }

    if not item:
        return {
            "code": std.get("code"),
            "title": std.get("title"),
            "status": "NOT_FOUND",
            "checkedAt": now,
            "error": "",
            "noticeNo": "",
            "announceDate": "",
            "effectiveDate": "",
            "revisionType": "",
            "htmlUrl": "",
            "sourceHash": "",
        }

    source_hash = sha256_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
    html_url = item.get("법령상세링크") or item.get("상세링크") or ""

    return {
        "code": std.get("code"),
        "title": std.get("title"),
        "status": "FOUND",
        "checkedAt": now,
        "error": "",
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


def diff_changed(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> Tuple[bool, List[str]]:
    keys = [
        "status",
        "noticeNo",
        "announceDate",
        "effectiveDate",
        "revisionType",
        "htmlUrl",
        "sourceHash",
        "error",
    ]

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
        f"NFPC {nfpc_stats['changed']}건 변경(전체 {nfpc_stats['total']} / 성공 {nfpc_stats['found']} / 미검출 {nfpc_stats['notFound']} / 오류 {nfpc_stats['error']}) | "
        f"NFTC {nftc_stats['changed']}건 변경(전체 {nftc_stats['total']} / 성공 {nftc_stats['found']} / 미검출 {nftc_stats['notFound']} / 오류 {nftc_stats['error']})"
    )

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

    short = f"[{TODAY}] {result} - NFPC {nfpc_stats['changed']}건, NFTC {nftc_stats['changed']}건"
    print(short)
    print(summary)

    if all_changes:
        post_webhook(f"{short}\n{summary}")


if __name__ == "__main__":
    main()
