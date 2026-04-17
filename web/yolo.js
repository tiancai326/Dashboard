const diagnostics = [
  {
    captureTime: "2026-04-13 10:22:15",
    zone: "Zone_3",
    result: "潜叶蛾",
    confidence: 92,
    status: "danger",
    statusBadge: "严重",
    desc: "检测到严重虫害，建议立即处理。潜叶蛾幼虫在叶片表皮下取食，形成弯曲的虫道。",
  },
  {
    captureTime: "2026-04-13 10:18:42",
    zone: "Zone_2",
    result: "叶片黄化",
    confidence: 85,
    status: "warn",
    statusBadge: "警告",
    desc: "检测到轻度病害，叶片出现黄化现象，可能缺氮或根系问题。",
  },
  {
    captureTime: "2026-04-13 10:15:30",
    zone: "Zone_5",
    result: "健康叶片",
    confidence: 98,
    status: "healthy",
    statusBadge: "正常",
    desc: "叶片健康，颜色正常，无病虫害迹象。",
  },
  {
    captureTime: "2026-04-13 10:12:18",
    zone: "Zone_1",
    result: "健康叶片",
    confidence: 97,
    status: "healthy",
    statusBadge: "正常",
    desc: "生长状态良好，叶片翠绿饱满。",
  },
  {
    captureTime: "2026-04-13 10:08:55",
    zone: "Zone_4",
    result: "健康叶片",
    confidence: 99,
    status: "healthy",
    statusBadge: "正常",
    desc: "优秀的生长状态，继续保持当前管理措施。",
  },
  {
    captureTime: "2026-04-13 09:58:32",
    zone: "Zone_3",
    result: "蚜虫",
    confidence: 88,
    status: "warn",
    statusBadge: "警告",
    desc: "发现蚜虫群落，建议使用生物防治或低毒去药剂。",
  },
  {
    captureTime: "2026-04-13 09:45:17",
    zone: "Zone_6",
    result: "健康叶片",
    confidence: 96,
    status: "healthy",
    statusBadge: "正常",
    desc: "叶片健康，无异常情况。",
  },
  {
    captureTime: "2026-04-13 09:32:05",
    zone: "Zone_2",
    result: "健康叶片",
    confidence: 95,
    status: "healthy",
    statusBadge: "正常",
    desc: "生长正常，保持现有管理。",
  },
];

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
  zone: [
    { value: "all", label: "全部区域" },
    { value: "Zone_1", label: "Zone_1" },
    { value: "Zone_2", label: "Zone_2" },
    { value: "Zone_3", label: "Zone_3" },
    { value: "Zone_4", label: "Zone_4" },
    { value: "Zone_5", label: "Zone_5" },
    { value: "Zone_6", label: "Zone_6" },
  ],
  status: [
    { value: "all", label: "看全部", dot: "green" },
    { value: "abnormal", label: "仅看异常预警", dot: "red" },
  ],
};

function parseCaptureTime(value) {
  return new Date(String(value).replace(" ", "T"));
}

function latestCaptureTime() {
  return diagnostics
    .map((x) => parseCaptureTime(x.captureTime))
    .reduce((max, curr) => (curr > max ? curr : max), new Date(0));
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
    今日共巡检图片 <span class="em">${diagnostics.length}</span> 张
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
        <article class="diag-card">
          <div class="thumb">
            <span class="badge-left ${item.status}">${item.statusBadge}</span>
            <span class="badge-right">${item.confidence}%</span>
            <div class="thumb-empty-text">待接入 YOLO 图像</div>
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
    const hitStatus = filters.status === "all" ? true : item.status !== "healthy";

    return hitTime && hitZone && hitStatus;
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

bindFilterEvents();
renderAll();
initSidebar();
