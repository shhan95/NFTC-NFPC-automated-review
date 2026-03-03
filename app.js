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
        <div class="item" data-code="${esc(s.code)}">
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
    .map((r) => {
      // 💡 새로 추가된 부분: 변경된 항목들을 순회하며 개정이유(reason)를 그려줍니다.
      let changesHtml = "";
      if (r.changes && r.changes.length > 0) {
        changesHtml = r.changes.map(c => {
          let box = `<div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--line-soft);">`;
          box += `<div class="small"><b>${esc(c.code)}</b> : ${esc(c.title)} <span class="muted">(${esc(c.revisionType || "변경")})</span></div>`;
          
          // 개정이유 데이터가 있다면 아까 만든 CSS(reasonBox)를 입혀서 출력!
          if (c.reason) {
            box += `<div class="reasonBox">
                      <div class="reasonLabel">개정이유 브리핑</div>
                      ${esc(c.reason)}
                    </div>`;
          }
          box += `</div>`;
          return box;
        }).join("");
      } else {
        changesHtml = `<div class="small" style="margin-top: 6px;">변경 항목: -</div>`;
      }

      return `
        <div class="logItem">
          <div class="logTop">
            <div><b>${esc(r.date)}</b></div>
            <div>${r.result === "변경 있음" ? '<span class="badge warn">변경 있음</span>' : '<span class="badge ok">변경 없음</span>'}</div>
          </div>
          <div class="small">${esc(r.summary || "")}</div>
          ${changesHtml}
        </div>
      `;
    })
    .join("");

  $("logList").innerHTML = html || `<div class="small">로그가 없습니다.</div>`;
}

function openDetail(code) {
  const list = loadCurrentList();
  const s = list.find((x) => x.code === code);
  const meta = loadCurrentSnapshot()[code] || {};

  $("dlgTitle").textContent = `${code} · ${s?.title || ""}`;
  $("dlgBody").innerHTML = `
    <table class="table">
      <tbody>
        <tr><th>상태</th><td>${esc(meta.status || "-")}</td></tr>
        <tr><th>제·개정구분</th><td>${esc(meta.revisionType || "-")}</td></tr>
        <tr><th>발령번호</th><td>${esc(meta.noticeNo || "-")}</td></tr>
        <tr><th>발령일</th><td>${esc(meta.announceDate || "-")}</td></tr>
        <tr><th>시행일</th><td>${esc(meta.effectiveDate || "-")}</td></tr>
        <tr><th>원문 링크</th><td>${meta.htmlUrl ? `<a href="${esc(meta.htmlUrl)}" target="_blank" rel="noreferrer">바로가기</a>` : "-"}</td></tr>
        <tr><th>오류</th><td>${esc(meta.error || "-")}</td></tr>
        <tr><th>최종 점검</th><td>${esc(meta.checkedAt || "-")}</td></tr>
      </tbody>
    </table>
  `;

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
