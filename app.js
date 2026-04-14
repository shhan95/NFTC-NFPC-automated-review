const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

let TAB = "nfpc";
let NFPC = [];
let NFTC = [];
let SNAP = { nfpc: {}, nftc: {} };
let LOG = { lastRun: null, records: [] };

function statusBadge(status) {
  if (status === "FOUND") return `<span class="badge ok">FOUND</span>`;
  if (status === "NOT_FOUND") return `<span class="badge warn">NOT_FOUND</span>`;
  return `<span class="badge err">ERROR</span>`;
}

function loadCurrentList() {
  return TAB === "nfpc" ? NFPC : NFTC;
}

function loadCurrentSnapshot() {
  return TAB === "nfpc" ? SNAP.nfpc || {} : SNAP.nftc || {};
}

function renderStats() {
  const latest = (LOG.records || [])[0] || {};
  $("nfpcCount").textContent = NFPC.length.toString();
  $("nftcCount").textContent = NFTC.length.toString();
  $("changeCount").textContent = String((latest.changes || []).length || 0);
  $("latestResult").textContent = latest.result || "-";
}

function renderStandards() {
  const q = $("searchInput").value.trim().toLowerCase();
  const f = $("statusFilter").value;
  const list = loadCurrentList();
  const snap = loadCurrentSnapshot();

  const html = list
    .filter((s) => {
      const status = (snap[s.code] || {}).status || "NOT_FOUND";
      const matchesFilter = f === "all" ? true : status === f;
      const matchesQuery = !q
        ? true
        : [s.code, s.title, s.query].join(" ").toLowerCase().includes(q);
      return matchesFilter && matchesQuery;
    })
    .map((s) => {
      const meta = snap[s.code] || { status: "NOT_FOUND" };
      return `
        <div class="item" data-code="${esc(s.code)}" style="cursor: pointer;">
          <div class="itemTop">
            <div>
              <div class="code">${esc(s.code)}</div>
              <div class="title">${esc(s.title)}</div>
            </div>
            ${statusBadge(meta.status)}
          </div>
          <div class="small">
            제·개정구분: ${esc(meta.revisionType || "-")} · 발령일: ${esc(meta.announceDate || "-")}
          </div>
        </div>
      `;
    })
    .join("");

  $("stdList").innerHTML = html || `<div class="small">표시할 항목이 없습니다.</div>`;

  document.querySelectorAll(".item").forEach((el) => {
    el.addEventListener("click", () => openDetail(el.dataset.code));
  });
}

// 💡 수정됨: 긴 상세 내역을 감추고 클릭을 유도하도록 변경
function renderLogs() {
  const records = LOG.records || [];
  const latest = records[0];

  if (latest) {
    $("summaryBox").innerHTML = `
      <div><b>${esc(latest.date)}</b> · ${esc(latest.result)}</div>
      <div class="small">${esc(latest.summary || "")}</div>
    `;
  } else {
    $("summaryBox").innerHTML = `<div>실행 이력이 없습니다.</div>`;
  }

  const html = records
    .map((r, index) => {
      return `
        <div class="logItem" data-index="${index}" style="cursor: pointer; padding: 12px; margin-bottom: 8px; border: 1px solid var(--line-soft, #ddd); border-radius: 6px;">
          <div class="logTop" style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <div><b>${esc(r.date)}</b></div>
            <div>${r.result === "변경 있음" ? '<span class="badge warn" style="color:red;">변경 있음</span>' : '<span class="badge ok" style="color:green;">변경 없음</span>'}</div>
          </div>
          <div class="small">${esc(r.summary || "")}</div>
          <div class="small muted" style="margin-top: 6px; color: #666;">👉 클릭하여 상세 내역 및 사유 확인</div>
        </div>
      `;
    })
    .join("");

  $("logList").innerHTML = html || `<div class="small">로그가 없습니다.</div>`;

  // 💡 추가됨: 로그 아이템 클릭 시 다이얼로그 오픈 이벤트 바인딩
  document.querySelectorAll(".logItem").forEach((el) => {
    el.addEventListener("click", () => {
      const idx = el.dataset.index;
      openLogDetail(records[idx]);
    });
  });
}

// 기존: 기준 목록(Standards) 클릭 시 상세 팝업
function openDetail(code) {
  const list = loadCurrentList();
  const s = list.find((x) => x.code === code);
  const meta = loadCurrentSnapshot()[code] || {};

  $("dlgTitle").textContent = `${code} · ${s?.title || ""}`;
  
  let finalUrl = meta.htmlUrl;
  if (!finalUrl && meta.seq) {
    finalUrl = `https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=${meta.seq}`;
  }

  let linkButton = finalUrl 
    ? `<div style="margin-top: 16px; text-align: center;">
         <a href="${esc(finalUrl)}" target="_blank" rel="noreferrer" style="display: block; padding: 14px; background: var(--accent); color: #0b1220; font-size: 15px; font-weight: 800; text-decoration: none; border-radius: 10px; transition: 0.2s;">
            📖 공식 법령 전문 보러가기 (새창)
         </a>
       </div>`
    : `<div style="margin-top: 16px; text-align: center; color: var(--warn); font-size: 14px;">원문 링크를 아직 불러올 수 없습니다.</div>`;

  $("dlgBody").innerHTML = `
    <table class="table">
      <tbody>
        <tr><th style="width: 30%;">상태</th><td>${statusBadge(meta.status)}</td></tr>
        <tr><th>제·개정구분</th><td>${esc(meta.revisionType || "-")}</td></tr>
        <tr><th>발령번호</th><td>${esc(meta.noticeNo || "-")}</td></tr>
        <tr><th>발령일</th><td>${esc(meta.announceDate || "-")}</td></tr>
        <tr><th>시행일</th><td>${esc(meta.effectiveDate || "-")}</td></tr>
        <tr><th>최종 점검</th><td>${esc(meta.checkedAt || "-")}</td></tr>
        ${meta.error ? `<tr><th>오류</th><td style="color: var(--err);">${esc(meta.error)}</td></tr>` : ""}
      </tbody>
    </table>
    ${linkButton}
  `;

  $("detailDialog").showModal();
}

// 💡 신규 추가됨: 이력(로그) 클릭 시 상세 팝업
function openLogDetail(record) {
  $("dlgTitle").textContent = `${esc(record.date)} 점검 상세 내역`;

  // 변경 내역이 없는 날짜인 경우
  if (!record.changes || record.changes.length === 0) {
    $("dlgBody").innerHTML = `<div style="padding: 20px; text-align: center; color: #666;">이 날짜에는 감지된 변경 사항이나 오류가 없습니다.</div>`;
    $("detailDialog").showModal();
    return;
  }

  // 표(Table) 헤더 구성
  let html = `
    <table class="table" style="width: 100%; text-align: left; border-collapse: collapse;">
      <thead>
        <tr style="border-bottom: 2px solid var(--line-soft, #ddd);">
          <th style="padding: 8px;">구분</th>
          <th style="padding: 8px;">법령명 (코드)</th>
          <th style="padding: 8px;">개정유형</th>
          <th style="padding: 8px;">비고 (개정이유 등)</th>
        </tr>
      </thead>
      <tbody>
  `;

  // 데이터 바인딩
  record.changes.forEach((c) => {
    // 뱃지 색상 하드코딩 (기존 style.css에 없을 수 있으므로 인라인 스타일 추가)
    const scopeBadge = c.scope === "NFPC" 
      ? `<span class="badge" style="background:#0366d6; color:white; padding:3px 6px; border-radius:4px;">NFPC</span>` 
      : `<span class="badge" style="background:#6f42c1; color:white; padding:3px 6px; border-radius:4px;">NFTC</span>`;
    
    // ERROR 상태 표시 처리
    const statusHtml = c.status === "ERROR" 
      ? `<span style="color:red; font-weight:bold;">ERROR</span>` 
      : esc(c.revisionType || "-");

    const reasonHtml = c.reason || (c.status === "ERROR" ? "데이터 수집 오류" : "-");

    html += `
      <tr style="border-bottom: 1px solid var(--line-soft, #eee);">
        <td style="padding: 8px;">${scopeBadge}</td>
        <td style="padding: 8px;">
          <b>${esc(c.code)}</b><br>
          <span style="font-size:13px; color:#555;">${esc(c.title)}</span>
        </td>
        <td style="padding: 8px;">${statusHtml}</td>
        <td style="padding: 8px; font-size:13px; line-height:1.4;">${esc(reasonHtml)}</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  
  $("dlgBody").innerHTML = html;
  $("detailDialog").showModal();
}

function bindEvents() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      TAB = btn.dataset.tab;
      renderStandards();
    });
  });

  $("searchInput").addEventListener("input", renderStandards);
  $("statusFilter").addEventListener("change", renderStandards);
  $("dlgClose").addEventListener("click", () => $("detailDialog").close());
  $("downloadBtn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(LOG, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "data.json";
    a.click();
    URL.revokeObjectURL(url);
  });
}

async function init() {
  const [nfpc, nftc, snap, log] = await Promise.all([
    fetch("./standards_nfpc.json", { cache: "no-store" }).then((r) => r.json()),
    fetch("./standards_nftc.json", { cache: "no-store" }).then((r) => r.json()),
    fetch("./snapshot.json", { cache: "no-store" }).then((r) => r.json()).catch(() => ({ nfpc: {}, nftc: {} })),
    fetch("./data.json", { cache: "no-store" }).then((r) => r.json()).catch(() => ({ lastRun: null, records: [] })),
  ]);

  NFPC = nfpc.items || [];
  NFTC = nftc.items || [];
  SNAP = snap;
  LOG = log;

  $("lastRun").textContent = `마지막 점검: ${LOG.lastRun || "-"}`;

  bindEvents();
  renderStats();
  renderStandards();
  renderLogs();
}

init();
