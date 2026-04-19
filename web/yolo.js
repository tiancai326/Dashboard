const diagnostics = [];

const cardGrid = document.getElementById("cardGrid");
const toolbarMeta = document.getElementById("toolbarMeta");
const appShell = document.getElementById("appShell");
const filterListEl = document.getElementById("filterList");

const filters = {
  time: "today",
  zone: "all",
  status: "all",
};

const filterOptions = {
  time: [
    { value: "today", label: "今天" },
    { value: "week", label: "本周" },
    { value: "month", label: "本月" },
  ],
  zone: [{ value: "all", label: "全部区域" }],
  status: [
    { value: "all", label: "看全部", dot: "green" },
    { value: "abnormal", label: "仅看异常预警", dot: "red" },
    { value: "healthy", label: "仅看健康样本", dot: "green" },
  ],
};

let modalEl = null;
let analyzingRecordId = "";

function parseCaptureTime(value) {
  return new Date(String(value).replace(" ", "T"));
}

function latestCaptureTime() {
  if (!diagnostics.length) return new Date();
  return diagnostics
    .map((x) => parseCaptureTime(x.captureTime))
    .reduce((max, curr) => (curr > max ? curr : max), new Date(0));
}

function normalizeRecord(r) {
  const severity = r.severity === "danger" ? "danger" : r.severity === "warn" ? "warn" : "healthy";
  const labels = (r.detections || []).map((d) => d.label);
  const uniqueLabels = [...new Set(labels)];
  const desc =
    r.description ||
    (uniqueLabels.length
      ? `检测到 ${r.detection_count || uniqueLabels.length} 个目标，标签: ${uniqueLabels.join("、")}`
      : "未检测到明显病虫害目标，叶片状态正常。");

  return {
    id: r.id,
    captureTime: r.capture_time || "--",
    zone: r.zone_id || "--",
    result: r.summary_label || "健康叶片",
    confidence: Math.round(Number(r.summary_confidence || 0) * 100),
    status: severity,
    statusBadge: severity === "danger" ? "警告" : severity === "warn" ? "异常" : "健康",
    desc,
    imageUrl: r.image_url || "",
    fileName: r.file_name || "",
    detections: r.detections || [],
    imageWidth: Number(r.image_width || 0),
    imageHeight: Number(r.image_height || 0),
    detectionCount: Number(r.detection_count || 0),
    levelText: r.level_text || "果树健康",
  };
}

function refreshZoneOptions() {
  const zones = [...new Set(diagnostics.map((x) => x.zone).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  filterOptions.zone = [{ value: "all", label: "全部区域" }, ...zones.map((z) => ({ value: z, label: z }))];
  if (filters.zone !== "all" && !zones.includes(filters.zone)) {
    filters.zone = "all";
  }
}

function initSidebar() {
  const collapseBtn = document.getElementById("collapseBtn");
  collapseBtn?.addEventListener("click", () => {
    appShell?.classList.toggle("sidebar-collapsed");
  });
}

function renderMeta(rows) {
  const abnormalCount = rows.filter((x) => x.status !== "healthy").length;
  const hotZoneCounter = rows
    .filter((x) => x.status !== "healthy")
    .reduce((acc, cur) => {
      acc[cur.zone] = (acc[cur.zone] || 0) + 1;
      return acc;
    }, {});
  const hotZone = Object.keys(hotZoneCounter).sort((a, b) => hotZoneCounter[b] - hotZoneCounter[a])[0] || "--";

  toolbarMeta.innerHTML = `
    已接入原图 <span class="em">${diagnostics.length}</span> 张
    &nbsp;&nbsp;&nbsp; 发现异常 <span class="warn">${abnormalCount}</span> 处
    &nbsp;&nbsp;&nbsp; 高发区域: <span class="hot">${hotZone}</span>
    &nbsp;&nbsp;&nbsp; 当前显示 <span class="em">${rows.length}</span> 条记录
  `;
}

function renderCards(rows) {
  if (!rows.length) {
    cardGrid.innerHTML = '<div class="empty-tip">当前筛选条件下暂无数据</div>';
    return;
  }

  cardGrid.innerHTML = rows
    .map((item) => {
      return `
        <article class="diag-card" data-id="${item.id}">
          <div class="thumb">
            <span class="badge-left ${item.status}">${item.statusBadge}</span>
            <span class="badge-right">${item.confidence}%</span>
            ${
              item.imageUrl
                ? `<img class="thumb-img" src="${item.imageUrl}" alt="${item.result}" loading="lazy">`
                : '<div class="thumb-empty-text">图片读取失败</div>'
            }
            <div class="thumb-marker">${item.detectionCount || 0} 个目标</div>
          </div>
          <div class="card-info">
            <div class="meta-time">⏰ ${item.captureTime}</div>
            <div class="meta-row">
              <span class="meta-zone">${item.zone}</span>
              <span class="meta-result ${item.status}">${item.result}</span>
            </div>
            <div class="meta-desc">${item.desc}</div>
          </div>
        </article>
      `;
    })
    .join("");
}

function getFilteredRows() {
  const latest = latestCaptureTime();

  return diagnostics.filter((item) => {
    const itemTime = parseCaptureTime(item.captureTime);

    const hitTime = (() => {
      if (filters.time === "week") {
        const diff = latest.getTime() - itemTime.getTime();
        return diff >= 0 && diff <= 7 * 24 * 60 * 60 * 1000;
      }
      if (filters.time === "month") {
        return itemTime.getFullYear() === latest.getFullYear() && itemTime.getMonth() === latest.getMonth();
      }
      return (
        itemTime.getFullYear() === latest.getFullYear() &&
        itemTime.getMonth() === latest.getMonth() &&
        itemTime.getDate() === latest.getDate()
      );
    })();

    const hitZone = filters.zone === "all" ? true : item.zone === filters.zone;
    const hitStatus =
      filters.status === "all" ? true : filters.status === "abnormal" ? item.status !== "healthy" : item.status === "healthy";

    return hitTime && hitZone && hitStatus;
  });
}

function ensureModal() {
  if (modalEl) return;
  modalEl = document.createElement("div");
  modalEl.className = "diag-modal";
  modalEl.innerHTML = `
    <div class="diag-modal-mask" data-close="1"></div>
    <div class="diag-modal-panel">
      <button class="diag-modal-close" type="button" data-close="1">×</button>
      <div class="diag-modal-left">
        <div class="diag-image-wrap">
          <img id="diagModalImage" class="diag-image" src="" alt="YOLO结果">
          <div id="diagOverlay" class="diag-overlay"></div>
        </div>
      </div>
      <div class="diag-modal-right">
        <h2 class="diag-modal-title">诊断详情</h2>
        <div class="diag-kv"><span>检测时间</span><strong id="diagCaptureTime">--</strong></div>
        <div class="diag-kv"><span>所属区域</span><strong id="diagZone">--</strong></div>
        <div class="diag-kv"><span>YOLO诊断</span><strong id="diagResult">--</strong></div>
        <div class="diag-kv"><span>置信度</span><strong id="diagConf">--</strong></div>
        <div class="diag-ai-box">
          <div class="diag-ai-title">AI 分析报告</div>
          <p id="diagAiText" class="diag-ai-text">等待点击后请求 Dify 分析...</p>
        </div>
        <div class="diag-dify-box">
          <div class="diag-dify-title">Dify AI 专家复诊</div>
          <button id="diagDifyBtn" class="diag-dify-btn" type="button">请求 AI 专家生成用药处方</button>
          <p id="diagDifyHint" class="diag-dify-hint">AI 将结合图片、气象数据、历史记录生成建议。</p>
        </div>
        <p id="diagDesc" class="diag-desc"></p>
        <div id="diagDetList" class="diag-det-list"></div>
      </div>
    </div>
  `;
  document.body.appendChild(modalEl);

  modalEl.addEventListener("click", (e) => {
    if (e.target.closest("[data-close='1']")) {
      modalEl.classList.remove("is-open");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      modalEl.classList.remove("is-open");
    }
  });

  modalEl.querySelector("#diagDifyBtn")?.addEventListener("click", async () => {
    const recordId = modalEl.getAttribute("data-record-id") || "";
    const item = diagnostics.find((x) => x.id === recordId);
    if (!item) return;
    await requestDifyAnalysis(item);
  });
}

async function postJson(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("not authenticated");
  }
  if (!resp.ok) {
    let detail = `${url} -> ${resp.status}`;
    try {
      const data = await resp.json();
      if (data?.detail) detail = data.detail;
    } catch (_) {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return resp.json();
}

async function requestDifyAnalysis(item) {
  const aiTextEl = document.getElementById("diagAiText");
  const hintEl = document.getElementById("diagDifyHint");
  const btnEl = document.getElementById("diagDifyBtn");
  if (!aiTextEl || !hintEl || !btnEl) return;

  if (!item.fileName) {
    aiTextEl.textContent = "缺少图片文件名，无法提交 Dify 分析。";
    return;
  }

  if (analyzingRecordId === item.id) return;
  analyzingRecordId = item.id;

  btnEl.disabled = true;
  btnEl.textContent = "正在生成专家建议...";
  hintEl.textContent = "请求已发出，请稍候。";
  aiTextEl.textContent = "Dify 正在分析图片与上下文信息...";

  try {
    const res = await postJson("/api/dify/analyze-image", {
      file_name: item.fileName,
      capture_time: item.captureTime,
      zone_id: item.zone,
      yolo_result: item.result,
      confidence: item.confidence,
      description: item.desc,
    });
    aiTextEl.textContent = res.text || "Dify 未返回可展示文本。";
    hintEl.textContent = `分析完成${res.status ? `（${res.status}）` : ""}`;
  } catch (err) {
    aiTextEl.textContent = `Dify 分析失败：${err.message}`;
    hintEl.textContent = "请检查 API Key、工作流输入变量或稍后重试。";
  } finally {
    btnEl.disabled = false;
    btnEl.textContent = "重新请求 AI 专家建议";
    analyzingRecordId = "";
  }
}

function openDetail(item) {
  ensureModal();
  const image = document.getElementById("diagModalImage");
  const overlay = document.getElementById("diagOverlay");

  image.src = item.imageUrl;
  modalEl.setAttribute("data-record-id", item.id);
  document.getElementById("diagCaptureTime").textContent = item.captureTime;
  document.getElementById("diagZone").textContent = item.zone;
  document.getElementById("diagResult").textContent = item.result;
  document.getElementById("diagConf").textContent = `${item.confidence}%`;
  document.getElementById("diagDesc").textContent = item.desc;

  overlay.innerHTML = "";
  document.getElementById("diagDetList").innerHTML = (item.detections || []).length
    ? item.detections
        .map((d) => `<div class="diag-det-chip">${d.label} · ${Math.round(Number(d.confidence || 0) * 100)}%</div>`)
        .join("")
    : '<div class="diag-det-chip is-ok">未检出异常目标</div>';

  const aiTextEl = document.getElementById("diagAiText");
  const hintEl = document.getElementById("diagDifyHint");
  const btnEl = document.getElementById("diagDifyBtn");
  if (aiTextEl) aiTextEl.textContent = "点击下方按钮后，将发送 YOLO 带框图给 Dify 生成建议。";
  if (hintEl) hintEl.textContent = "默认不自动发送。请手动点击请求 AI 专家建议。";
  if (btnEl) {
    btnEl.disabled = false;
    btnEl.textContent = "请求 AI 专家生成用药处方";
  }

  modalEl.classList.add("is-open");
  fetchJson(`/api/yolo-annotated?file_name=${encodeURIComponent(item.fileName)}`)
    .then((res) => {
      if (res?.annotated_image_url) {
        image.src = res.annotated_image_url;
      }
    })
    .catch(() => {
      // Keep original image if annotated image generation fails.
    });
}

function closeAllDropdowns() {
  filterListEl.querySelectorAll(".filter-dropdown").forEach((el) => el.classList.remove("is-open"));
}

function renderFilterMenus() {
  const timeMenu = document.getElementById("timeFilterMenu");
  const zoneMenu = document.getElementById("zoneFilterMenu");
  const statusMenu = document.getElementById("statusFilterMenu");

  const buildOptions = (key, opts) =>
    opts
      .map((opt) => {
        const active = filters[key] === opt.value ? "is-active" : "";
        const dot = opt.dot ? `<span class="filter-dot ${opt.dot}"></span>` : "";
        const mark = filters[key] === opt.value ? '<span class="filter-opt-mark">✓</span>' : "";
        return `<button class="filter-opt ${active}" type="button" data-filter-key="${key}" data-filter-value="${opt.value}">${dot}${opt.label}${mark}</button>`;
      })
      .join("");

  timeMenu.innerHTML = buildOptions("time", filterOptions.time);
  zoneMenu.innerHTML = buildOptions("zone", filterOptions.zone);
  statusMenu.innerHTML = buildOptions("status", filterOptions.status);

  const timeLabel = filterOptions.time.find((x) => x.value === filters.time)?.label || "今天";
  const zoneLabel = filterOptions.zone.find((x) => x.value === filters.zone)?.label || "全部区域";
  const statusOpt = filterOptions.status.find((x) => x.value === filters.status) || filterOptions.status[0];

  document.querySelector("#timeFilterBtn .filter-value").textContent = timeLabel;
  document.querySelector("#zoneFilterBtn .filter-value").textContent = zoneLabel;
  document.querySelector("#statusFilterBtn .filter-value").textContent = statusOpt.label;
  document.querySelector("#statusFilterBtn .filter-icon").textContent = statusOpt.dot === "red" ? "🔴" : "🟢";
}

function bindFilterEvents() {
  filterListEl.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const dropdown = btn.closest(".filter-dropdown");
      const shouldOpen = !dropdown.classList.contains("is-open");
      closeAllDropdowns();
      if (shouldOpen) dropdown.classList.add("is-open");
    });
  });

  filterListEl.addEventListener("click", (e) => {
    const target = e.target.closest(".filter-opt");
    if (!target) return;

    const key = target.dataset.filterKey;
    const value = target.dataset.filterValue;
    filters[key] = value;

    closeAllDropdowns();
    renderAll();
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".filter-dropdown")) {
      closeAllDropdowns();
    }
  });
}

function renderAll() {
  renderFilterMenus();
  const rows = getFilteredRows();
  renderMeta(rows);
  renderCards(rows);
}

function bindCardEvents() {
  cardGrid.addEventListener("click", (e) => {
    const card = e.target.closest(".diag-card");
    if (!card) return;
    const id = card.getAttribute("data-id");
    const item = diagnostics.find((x) => x.id === id);
    if (item) openDetail(item);
  });
}

async function fetchJson(url) {
  const resp = await fetch(url);
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("not authenticated");
  }
  if (!resp.ok) throw new Error(`${url} -> ${resp.status}`);
  return resp.json();
}

async function loadDetections() {
  const data = await fetchJson("/api/yolo-detections?limit=200");
  diagnostics.length = 0;
  (data.records || []).forEach((r) => diagnostics.push(normalizeRecord(r)));
  refreshZoneOptions();
  renderAll();
}

async function bootstrap() {
  bindFilterEvents();
  bindCardEvents();
  initSidebar();
  await loadDetections();
}
bootstrap();
