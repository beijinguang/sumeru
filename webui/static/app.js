/* 须弥写作驾驶舱（原生 JS，无依赖） */
"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { error: text }; }
  return { ok: res.ok, status: res.status, data };
}

/* 与后端统一口径：剥离「第X章」标题行，汉字+英文单词计数 */
function countWords(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  while (lines.length && !lines[0].trim()) lines.shift();
  if (lines.length && /^\s*第\s*\d+\s*章/.test(lines[0])) lines.shift();
  const body = lines.join("\n");
  const hanzi = (body.match(/[\u4e00-\u9fa5]/g) || []).length;
  const english = (body.match(/[a-zA-Z]+/g) || []).length;
  return hanzi + english;
}

/* ------------------------------------------------ 导航 */
function switchPage(name) {
  $$(".page").forEach((p) => p.classList.add("hidden"));
  $(`#page-${name}`).classList.remove("hidden");
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === name));
  const loaders = {
    dashboard: loadDashboard, chapters: loadChapters,
    tools: initTools, export: initExport, assistant: loadAssistant,
  };
  (loaders[name] || (() => {}))();
}
$$(".nav-btn").forEach((b) => b.addEventListener("click", () => switchPage(b.dataset.page)));

/* ------------------------------------------------ ① 仪表盘 */
async function loadDashboard() {
  const { data } = await fetchJSON("/api/status");
  if (data.error) { $("#stat-cards").innerHTML = `<div class="empty">${data.error}</div>`; return; }

  const cards = [
    { label: "规划章节数", num: data.totalChaptersPlanned ?? "—" },
    { label: "已写章节", num: data.chapterCount },
    { label: "总字数", num: data.wordStats ? data.wordStats.total_words.toLocaleString() : "—" },
    { label: "平均章字数", num: data.wordStats ? Math.round(data.wordStats.average_words).toLocaleString() : "—" },
  ];
  $("#stat-cards").innerHTML = cards.map(
    (c) => `<div class="card"><div class="num">${c.num}</div><div class="label">${c.label}</div></div>`
  ).join("");

  const dot = (g) => g.passed === true ? "pass" : g.passed === false ? "fail" : "";
  $("#gate-list").innerHTML = data.gates.map(
    (g) => `<div class="gate" title="${g.detail || ""}"><span class="dot ${dot(g)}"></span>${g.stage}</div>`
  ).join("");
  $("#gate-mini").innerHTML = data.gates.map(
    (g) => `<span class="dot ${dot(g)}" title="${g.stage}"></span>`
  ).join("");

  await loadWordChart();
}

async function loadWordChart() {
  const { data } = await fetchJSON("/api/reports/.sumeru/review/word-count.json");
  const chart = $("#word-chart");
  if (data.error || !data.content || !data.content.chapters) {
    chart.classList.add("empty"); return;
  }
  chart.classList.remove("empty");
  const ideal = data.content.summary.ideal_range || [3000, 5000];
  const max = Math.max(...data.content.chapters.map((c) => c.total_words), ideal[1]);
  chart.innerHTML = data.content.chapters.map((c) => {
    const h = Math.max(4, Math.round(c.total_words / max * 100));
    const cls = c.total_words < ideal[0] ? "short" : c.total_words > ideal[1] ? "long" : "";
    return `<div class="bar ${cls}" style="height:${h}%" title="${c.file_name}：${c.total_words} 字"></div>`;
  }).join("");
  $("#chart-legend").innerHTML =
    `理想区间 ${ideal[0]}-${ideal[1]} 字 · <span style="color:var(--bad)">■</span> 过短 · ` +
    `<span style="color:var(--warn)">■</span> 过长 · 共 ${data.content.summary.total_words.toLocaleString()} 字`;
}

/* ------------------------------------------------ ② 章节管理 */
let currentChapter = null;
let originalContent = null;

async function loadChapters() {
  const { data } = await fetchJSON("/api/chapters");
  if (data.error) { $("#chapter-list").innerHTML = `<div class="empty">${data.error}</div>`; return; }
  const items = data.chapters.map(
    (c) => `<div class="chapter-item" data-num="${c.number}"><span>第${c.number}章</span><span>${c.title}</span></div>`
  ).join("");
  const invalid = data.invalid.map((n) => `<div class="chapter-item invalid"><span>${n}</span><span>命名错误</span></div>`).join("");
  $("#chapter-list").innerHTML = items + invalid;
  $$("#chapter-list .chapter-item[data-num]").forEach((el) =>
    el.addEventListener("click", () => openChapter(el.dataset.num)));
  if (data.chapters.length) openChapter(data.chapters[0].number);
  else $("#chapter-readonly").textContent = "chapters/ 目录还没有章节";
}

async function openChapter(num) {
  $$("#chapter-list .chapter-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.num === String(num)));
  const { data } = await fetchJSON(`/api/chapters/${num}?outline=1`);
  if (data.error) { $("#chapter-readonly").textContent = data.error; return; }
  currentChapter = num;
  originalContent = data.content;
  $("#chapter-meta").textContent = `${data.file}${data.hasOriginal ? " · 已有最初原稿备份" : " · 修改后首次保存将备份原稿"}`;
  setEditorMode(false);
  $("#chapter-readonly").textContent = data.content;
  updateWordCount();
  renderOutline(data.outline);
}

function setEditorMode(editing) {
  $("#chapter-editor").classList.toggle("hidden", !editing);
  $("#chapter-readonly").classList.toggle("hidden", editing);
  $("#btn-edit").classList.toggle("hidden", editing);
  $("#btn-save").classList.toggle("hidden", !editing);
  $("#btn-cancel").classList.toggle("hidden", !editing);
}

function updateWordCount() {
  const text = $("#chapter-editor").classList.contains("hidden")
    ? $("#chapter-readonly").textContent : $("#chapter-editor").value;
  $("#chapter-words").textContent = `字数：${countWords(text).toLocaleString()}（剥离标题行）`;
}

function renderOutline(outline) {
  if (!outline) { $("#outline-panel").textContent = ""; return; }
  const lines = [
    `【细纲对照】${outline.chapterTitle || ""}`,
    outline.coreEvent && `核心事件：${outline.coreEvent}`,
    outline.coolPoint && `爽点：${outline.coolPoint}`,
    outline.suspense && `悬念：${outline.suspense}`,
    outline.connection && `衔接：${outline.connection}`,
    Array.isArray(outline.plotProgression) && outline.plotProgression.length
      ? `推进节点：\n  - ${outline.plotProgression.join("\n  - ")}` : "",
  ].filter(Boolean);
  $("#outline-panel").textContent = lines.join("\n");
}

$("#btn-edit").addEventListener("click", () => {
  $("#chapter-editor").value = originalContent;
  setEditorMode(true);
  updateWordCount();
});
$("#btn-cancel").addEventListener("click", () => setEditorMode(false));
$("#chapter-editor").addEventListener("input", updateWordCount);
$("#btn-save").addEventListener("click", async () => {
  if (currentChapter == null) return;
  const content = $("#chapter-editor").value;
  const btn = $("#btn-save");
  btn.disabled = true;
  const { ok, data } = await fetchJSON(`/api/chapters/${currentChapter}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  btn.disabled = false;
  if (ok) {
    originalContent = content;
    setEditorMode(false);
    $("#chapter-readonly").textContent = content;
    $("#chapter-meta").textContent += " · 已保存";
    if (data.backups && data.backups.original) {
      $("#chapter-meta").textContent += "（备份见 .sumeru/write/）";
    }
    updateWordCount();
  } else {
    alert(`保存失败：${data.error || "未知错误"}`);
  }
});

/* ------------------------------------------------ ③ 工具面板 */
let toolsInited = false;

function buildArgs(name) {
  switch (name) {
    case "counter": {
      const args = ["--dir", $("#tc-counter-dir").value,
        "--min", $("#tc-counter-min").value, "--max", $("#tc-counter-max").value];
      return args;
    }
    case "check": {
      const args = ["--chapters", $("#tc-check-chapters").value,
        "--outline", $("#tc-check-outline").value];
      if ($("#tc-check-strict").checked) args.push("--strict");
      return args;
    }
    case "timeline":
      return ["--timeline", $("#tc-timeline-file").value];
    case "build": {
      const args = ["--chapters", $("#tc-build-chapters").value,
        "--platform", $("#tc-build-platform").value,
        "--format", $("#tc-build-formats").value];
      const title = $("#tc-build-title").value.trim();
      if (title) args.push("--title", title);
      if ($("#tc-build-checkonly").checked) args.push("--check-only");
      return args;
    }
    case "sensitive":
      return ["--dir", $("#tc-sensitive-dir").value];
    case "analyze": {
      const file = $("#tc-analyze-file").value.trim();
      const dir = $("#tc-analyze-dir").value.trim();
      return file ? ["--file", file] : dir ? ["--chapters", dir] : [];
    }
    default:
      return [];
  }
}

const TOOL_LABELS = {
  counter: "字数统计", check: "章节结构校验", timeline: "时间线校验",
  build: "完稿检查/导出", sensitive: "敏感词扫描", analyze: "拆书分析",
  plan: "章节规划", derivative: "原创性检查",
};

async function runTool(tool, builder) {
  const box = $("#tool-result");
  box.classList.remove("empty");
  box.innerHTML = `<span class="badge" style="background:var(--accent);color:#fff">运行中…</span>`;
  const { ok, data } = await fetchJSON(`/api/tools/${tool}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ args: buildArgs(builder) }),
  });
  renderToolResult(data, ok);
  if (tool === "counter" && data.exitCode === 0 && $("#page-dashboard")) loadWordChart();
}

function renderToolResult(data, ok) {
  if (!ok || data.error) {
    $("#tool-result").innerHTML = `<span class="badge fail">${data.error}</span>`;
    return;
  }
  const badge = data.exitCode === 0 ? '<span class="badge pass">✅ 通过 (0)</span>'
    : data.exitCode === -1 ? `<span class="badge timeout">⏱ 超时</span>`
    : `<span class="badge fail">❌ 退出码 ${data.exitCode}</span>`;
  $("#tool-result").innerHTML =
    `${badge}<div><b>${TOOL_LABELS[data.tool] || data.tool}</b></div>` +
    (data.stdout ? `<div style="margin-top:8px">${escapeHtml(data.stdout)}</div>` : "") +
    (data.stderr ? `<div style="color:var(--bad);margin-top:8px">${escapeHtml(data.stderr)}</div>` : "");
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function initTools() {
  if (toolsInited) return;
  toolsInited = true;
  $$(".run-tool").forEach((btn) =>
    btn.addEventListener("click", () => runTool(btn.dataset.tool, btn.dataset.builder)));
  initReportTabs();
}

const REPORTS = [
  [".sumeru/review/word-count.md", "字数统计"],
  [".sumeru/write/chapter-check.md", "章节结构校验"],
  [".sumeru/deconstruct/derivative-check.md", "原创性检查"],
  [".sumeru/finalize/report.md", "完稿校验"],
  ["完稿校验报告.md", "完稿报告(可见)"],
];

function initReportTabs() {
  $("#report-tabs").innerHTML = REPORTS.map(([path, label], i) =>
    `<span class="report-tab" data-i="${i}">${label}</span>`).join("");
  $$(".report-tab").forEach((tab) => tab.addEventListener("click", async () => {
    $$(".report-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const [path] = REPORTS[tab.dataset.i];
    const view = $("#report-view");
    view.classList.remove("empty");
    const { data } = await fetchJSON(`/api/reports/${encodeURIComponent(path)}`);
    view.innerHTML = data.error ? `<span class="empty">${data.error}</span>`
      : renderMarkdown(data.content);
  }));
}

function renderMarkdown(md) {
  const esc = escapeHtml(md);
  return esc
    .replace(/^# (.+)$/gm, "<h1>$1</h1>").replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/^\|(.+)\|$/gm, (m) => `<table><tr>${m.slice(1, -1).split("|").map((c) => `<td>${c.trim()}</td>`).join("")}</tr></table>`)
    .replace(/<\/table>\n<table>/g, "")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/^(?!<[hlpbt])(.+)$/gm, "<p>$1</p>");
}

/* ------------------------------------------------ ④ 导出中心 */
let exportInited = false;

function initExport() {
  if (exportInited) return;
  exportInited = true;
  $("#btn-export").addEventListener("click", async () => {
    const btn = $("#btn-export");
    const result = $("#export-result");
    btn.disabled = true;
    result.classList.remove("empty");
    result.innerHTML = "导出中…（全书导出约需数十秒）";
    const args = ["--chapters", "chapters",
      "--platform", $("#export-platform").value,
      "--format", $("#export-formats").value.trim()];
    const title = $("#export-title").value.trim();
    const author = $("#export-author").value.trim();
    if (title) args.push("--title", title);
    if (author) args.push("--author", author);
    const { ok, data } = await fetchJSON("/api/tools/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
    });
    btn.disabled = false;
    if (!ok || data.error) {
      result.innerHTML = `<span class="badge fail">${data.error}</span>`;
      return;
    }
    renderToolResult(data, ok);
    result.scrollIntoView({ behavior: "smooth" });
    await listExportFiles();
  });
  listExportFiles();
}

async function listExportFiles() {
  const platforms = ["qidian", "fanqie", "jjwxc", "zongheng", "17k"];
  const names = ["full.md", "full.txt", "full.html", "book.epub"];
  const rows = [];
  for (const p of platforms) {
    for (const n of names) {
      const res = await fetch(`/api/export/${p}/${n}`, { method: "HEAD" });
      if (res.ok) rows.push(`<div class="export-file"><span>${p}</span><a href="/api/export/${p}/${n}">下载 ${n}</a></div>`);
    }
  }
  $("#export-files").innerHTML = rows.length ? rows.join("")
    : '<div class="empty">暂无导出产物。注意：导出前需通过完稿校验（门禁绿灯）。</div>';
}

/* ------------------------------------------------ ⑤ 指令助手 */
async function loadAssistant() {
  const { data } = await fetchJSON("/api/next-step");
  const box = $("#next-step");
  if (data.error) { box.innerHTML = `<span class="empty">${data.error}</span>`; return; }
  box.innerHTML =
    `<div>阶段：<b>${data.stage}</b> — ${data.reason}</div>` +
    `<code class="cmd">${escapeHtml(data.command)}</code>` +
    `<button class="btn copy-btn" data-cmd="${escapeHtml(data.command)}">复制指令</button>` +
    `<div class="muted" style="margin-top:8px">${data.tip}</div>`;
  box.querySelector(".copy-btn").addEventListener("click", async (e) => {
    await navigator.clipboard.writeText(e.target.dataset.cmd);
    e.target.textContent = "✅ 已复制";
    setTimeout(() => (e.target.textContent = "复制指令"), 1500);
  });
}

/* ------------------------------------------------ 启动 */
switchPage("dashboard");
