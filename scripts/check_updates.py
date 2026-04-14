def post_webhook(record: Dict[str, Any]) -> None:
    if not ALERT_WEBHOOK_URL:
        print("⚠️ 알림 실패: 깃허브 Secret에 'ALERT_WEBHOOK_URL'이 없습니다!")
        return
        
    target_url = ALERT_WEBHOOK_URL
    if target_url.endswith("/slack"):
        target_url = target_url[:-6]

    # 기본 메시지 포장
    payload_dict = {
        "content": f"🔔 **[{record['date']}]** 점검 결과: **{record['result']}** ({record['summary']})"
    }

    # 변경 사항이 있다면 디스코드 Embed(카드형) 조립
    if record["changes"]:
        embeds = []
        for c in record["changes"]:
            # 에러 상태일 경우 빨간색(16711680), 아닐 경우 파란색(3447003)
            color_code = 16711680 if c["status"] == "ERROR" else 3447003
            
            # 개정이유가 없거나 에러일 때 텍스트 처리
            reason_text = c.get('reason', '')
            if not reason_text:
                reason_text = "별도의 개정이유가 제공되지 않았습니다." if c["status"] != "ERROR" else "API 수집 오류"
            
            embed = {
                "title": f"[{c['scope']}] {c['title']}",
                "color": color_code,
                "fields": [
                    {"name": "코드", "value": c['code'], "inline": True},
                    {"name": "상태", "value": c['status'], "inline": True},
                    {"name": "개정유형", "value": c.get('revisionType', '-'), "inline": True},
                    {"name": "시행일", "value": c.get('effectiveDate', '-'), "inline": True},
                    {"name": "💡 개정이유 / 비고", "value": reason_text[:1024]} # 디스코드 제한 1024자
                ]
            }
            # 링크가 있으면 추가
            if c.get("url"):
                embed["url"] = c["url"]
                
            embeds.append(embed)
            
        # 디스코드 웹훅은 한 번에 최대 10개의 임베드만 전송 가능
        payload_dict["embeds"] = embeds[:10]
        
        if len(record["changes"]) > 10:
            payload_dict["content"] += f"\n*(총 {len(record['changes'])}건의 변경이 감지되었습니다. 10건만 표시되며, 상세 내용은 대시보드를 확인하세요.)*"

    payload = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        target_url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=8).read()
        print("🔔 디스코드 알림 전송 성공!")
    except Exception as e:
        print(f"❌ 디스코드 알림 전송 실패: {e}")


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

    # 🌟 수정한 post_webhook 실행 (문자열이 아닌 record 딕셔너리 자체를 넘깁니다)
    post_webhook(record)

if __name__ == "__main__":
    main()
