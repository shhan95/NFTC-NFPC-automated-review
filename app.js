const $ = (id) => document.getElementById(id);
const esc = (s) => (s ?? "").toString()
  .replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")
  .replaceAll('"',"&quot;").replaceAll("'","&#039;");
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
let SNAP = { nfpc:{}, nftc:{} };

function badge(text){
  return text === "변경 없음"
    ? `<span class="badge ok">변경 없음</span>`
    : `<span class="badge warn">변경 있음</span>`;
function statusBadge(status) {
  if (status === "FOUND") return `<span class="badge ok">FOUND</span>`;
  if (status === "NOT_FOUND") return `<span class="badge warn">NOT_FOUND</span>`;
  return `<span class="badge err">ERROR</span>`;
}

function stdStatus(code){
  // 최신 로그에서 해당 code가 변경으로 등장했는지(가벼운 표시)
  for(const r of LOG.records){
    if(r.result === "변경 있음" && (r.changes||[]).some(c=>c.code===code)) return "변경 있음";
  }
  return "변경 없음";
function loadCurrentList() {
  return TAB === "nfpc" ? NFPC : NFTC;
}

function loadCurrentSnapshot() {
  return TAB === "nfpc" ? SNAP.nfpc || {} : SNAP.nftc || {};
}

function renderStandards(){
  const q = $("searchStd").value.trim().toLowerCase();
  const list = TAB === "nfpc" ? NFPC : NFTC;

  const rows = list.filter(x=>{
    if(!q) return true;
    return [x.code,x.title].join(" ").toLowerCase().includes(q);
  }).map(x=>{
    const st = stdStatus(x.code);
    return `
      <div class="item" data-code="${esc(x.code)}" data-tab="${esc(TAB)}">
        <div class="itemTop">
          <div>
            <div class="code">${esc(x.code)}</div>
            <div class="title">${esc(x.title || "")}</div>
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
          ${badge(st)}
        </div>
        <div class="small">검색어: ${esc(x.query || x.title || "")}</div>
      </div>
    `;
  }).join("");
      `;
    })
    .join("");

  $("stdList").innerHTML = rows || `<div class="small">표시할 항목이 없습니다.</div>`;
  $("stdList").innerHTML = html || `<div class="small">표시할 항목이 없습니다.</div>`;

  document.querySelectorAll(".item").forEach(el=>{
    el.addEventListener("click", ()=> openStd(el.dataset.tab, el.dataset.code));
  document.querySelectorAll(".item").forEach((el) => {
    el.addEventListener("click", () => openDetail(el.dataset.code));
  });
}

function renderLogs(){
  const rf = $("resultFilter").value;
  const rows = LOG.records
    .filter(r=>{
      if(rf==="nochange") return r.result==="변경 없음";
      if(rf==="change") return r.result==="변경 있음";
      return true;
    })
    .map(r=>`
      <div class="logRow">
        <div class="logRowHead">
          <div><b>${esc(r.date)}</b> <span class="small">${esc(r.scope||"NFPC/NFTC")}</span></div>
          ${badge(r.result)}
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
    .map((r) => `
      <div class="logItem">
        <div class="logTop">
          <div><b>${esc(r.date)}</b></div>
          <div>${r.result === "변경 있음" ? '<span class="badge warn">변경 있음</span>' : '<span class="badge ok">변경 없음</span>'}</div>
        </div>
        <div class="small">${esc(r.summary||"")}</div>
        <div class="small"><b>변경:</b> ${(r.changes||[]).map(c=>esc(c.code)).join(", ") || "-"}</div>
        <div class="small">${esc(r.summary || "")}</div>
        <div class="small">변경 항목: ${(r.changes || []).slice(0, 10).map((c) => esc(c.code)).join(", ") || "-"}</div>
      </div>
    `).join("");
    `)
    .join("");

  $("logList").innerHTML = rows || `<div class="small">로그가 없습니다.</div>`;
  $("logList").innerHTML = html || `<div class="small">로그가 없습니다.</div>`;
}

function openStd(tab, code){
  const list = tab==="nfpc" ? NFPC : NFTC;
  const s = list.find(x=>x.code===code);
  const snap = (SNAP[tab]||{})[code];

  const originLink = snap?.detailUrl || snap?.detailLink || "";
  const originHtmlLink = snap?.htmlUrl || "";

  $("dlgTitle").innerHTML = `${esc(code)} · ${esc(s?.title||"")}`;
  $("dlgSub").innerHTML = `${tab.toUpperCase()} · 원문: ${
    originHtmlLink ? `<a href="${esc(originHtmlLink)}" target="_blank" rel="noreferrer">법제처(원문)</a>` : "자동검토 후 생성"
  }`;
function openDetail(code) {
  const list = loadCurrentList();
  const s = list.find((x) => x.code === code);
  const meta = loadCurrentSnapshot()[code] || {};

  const meta = snap ? `
    <table class="tbl">
      <thead><tr><th>항목</th><th>값</th></tr></thead>
  $("dlgTitle").textContent = `${code} · ${s?.title || ""}`;
  $("dlgBody").innerHTML = `
    <table class="table">
      <tbody>
        <tr><td>고시번호</td><td>${esc(snap.noticeNo||"-")}</td></tr>
        <tr><td>발령일</td><td>${esc(snap.announceDate||"-")}</td></tr>
        <tr><td>시행일</td><td>${esc(snap.effectiveDate||"-")}</td></tr>
        <tr><td>제·개정구분</td><td>${esc(snap.revisionType||"-")}</td></tr>
        <tr><td>최종확인</td><td>${esc(snap.checkedAt||"-")}</td></tr>
        <tr><td>원문(HTML)</td><td>${originHtmlLink ? `<a href="${esc(originHtmlLink)}" target="_blank" rel="noreferrer">${esc(originHtmlLink)}</a>` : "-"}</td></tr>
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
  ` : `<div class="small">스냅샷 정보가 없습니다(첫 자동검토 이후 생성).</div>`;

  $("dlgBody").innerHTML = `
    <div class="small">
      * 자동검토는 법제처 OPEN API로 ‘행정규칙(고시)’ 메타(발령/시행/발령번호/제개정구분/본문 해시)를 수집해 변경 여부를 판단합니다.
      <br/>* 조문·별표 신구대비는 별도(부가) API가 필요할 수 있어 기본값은 “원문 확인”으로 표기됩니다.
    </div>
    ${meta}
  `;
  $("dlg").showModal();
}

function downloadJson(){
  const blob = new Blob([JSON.stringify(LOG,null,2)], {type:"application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "data.json";
  a.click();
  URL.revokeObjectURL(url);
  $("detailDialog").showModal();
}

async function init(){
  const [nfpc,nftc,log,snap] = await Promise.all([
    fetch("./standards_nfpc.json",{cache:"no-store"}).then(r=>r.json()),
    fetch("./standards_nftc.json",{cache:"no-store"}).then(r=>r.json()),
    fetch("./data.json",{cache:"no-store"}).then(r=>r.json()),
    fetch("./snapshot.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({nfpc:{},nftc:{}}))
  ]);
  NFPC = nfpc.items || [];
  NFTC = nftc.items || [];
  LOG = log;
  SNAP = snap;

  $("lastRun").textContent = `마지막 자동검토: ${LOG.lastRun || "-"}`;

  document.querySelectorAll(".tab").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
function bindEvents() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      TAB = btn.dataset.tab;
      renderStandards();
    });
  });

  $("searchStd").addEventListener("input", renderStandards);
  $("resultFilter").addEventListener("change", renderLogs);
  $("downloadJson").addEventListener("click", downloadJson);
  $("dlgClose").addEventListener("click", ()=> $("dlg").close());
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
  renderStandards();
  renderLogs();
}

init();
