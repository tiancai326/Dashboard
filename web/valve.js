const metricConfig = [
  { key: "air_temp", label: "空温", unit: "℃", digits: 1 },
  { key: "air_humidity", label: "空湿", unit: "%", digits: 1 },
  { key: "light_intensity", label: "光照", unit: "Lux", digits: 0 },
  { key: "soil_temp", label: "土温", unit: "℃", digits: 1 },
  { key: "soil_humidity", label: "土湿", unit: "%", digits: 1 },
  { key: "ec", label: "EC", unit: "mS/cm", digits: 2 },
  { key: "ph", label: "pH", unit: "", digits: 2 },
  { key: "n", label: "氮", unit: "mg/kg", digits: 0 },
  { key: "p", label: "磷", unit: "mg/kg", digits: 0 },
  { key: "k", label: "钾", unit: "mg/kg", digits: 0 },
];

let currentZone = "zone_1";
const valveStateByZone = {
  zone_1: { water: false, fertilizer: false },
  zone_2: { water: false, fertilizer: false },
  zone_3: { water: false, fertilizer: false },
  zone_4: { water: false, fertilizer: false },
  zone_5: { water: false, fertilizer: false },
  zone_6: { water: false, fertilizer: false },
};

const zoneSelectorEl = document.getElementById("zoneSelector");
const sensorTitleEl = document.getElementById("sensorTitle");
const sensorTimestampEl = document.getElementById("sensorTimestamp");
const sensorListEl = document.getElementById("sensorList");
const valveZoneTextEl = document.getElementById("valveZoneText");
const waterValveStatusEl = document.getElementById("waterValveStatus");
const fertValveStatusEl = document.getElementById("fertValveStatus");
const waterValveBtn = document.getElementById("waterValveBtn");
const fertValveBtn = document.getElementById("fertValveBtn");
const valveHintEl = document.getElementById("valveHint");
const appShell = document.getElementById("appShell");

function zoneText(zoneId) {
  return zoneId.replace("zone_", "Zone_");
}

function getNum(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "--";
  return Number(v).toFixed(digits);
}

function renderZoneButtons() {
  zoneSelectorEl.innerHTML = [1, 2, 3, 4, 5, 6]
    .map(
      (i) => `
        <button class="zone-btn ${currentZone === `zone_${i}` ? "is-active" : ""}" data-zone="zone_${i}" type="button">
          ${zoneText(`zone_${i}`)}
        </button>
      `
    )
    .join("");

  zoneSelectorEl.querySelectorAll(".zone-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      currentZone = btn.dataset.zone;
      renderZoneButtons();
      renderValveState();
      await loadZoneMetrics();
    });
  });
}

function renderMetrics(metrics = {}) {
  sensorTitleEl.textContent = `${zoneText(currentZone)} 传感器（10项）`;
  sensorListEl.innerHTML = metricConfig
    .map(
      (m) => `
        <div class="sensor-item">
          <div class="sensor-name">${m.label}</div>
          <div class="sensor-value">${getNum(metrics[m.key], m.digits)}<span class="sensor-unit">${m.unit}</span></div>
        </div>
      `
    )
    .join("");
}

function renderValveState() {
  const state = valveStateByZone[currentZone] || { water: false, fertilizer: false };
  const waterOn = Boolean(state.water);
  const fertOn = Boolean(state.fertilizer);
  const zone = zoneText(currentZone);

  valveZoneTextEl.textContent = zone;

  waterValveStatusEl.textContent = `当前状态：${waterOn ? "开启" : "关闭"}`;
  waterValveBtn.textContent = waterOn ? "开启" : "关闭";
  waterValveBtn.classList.toggle("is-on", waterOn);
  waterValveBtn.classList.toggle("is-off", !waterOn);

  fertValveStatusEl.textContent = `当前状态：${fertOn ? "开启" : "关闭"}`;
  fertValveBtn.textContent = fertOn ? "开启" : "关闭";
  fertValveBtn.classList.toggle("is-on", fertOn);
  fertValveBtn.classList.toggle("is-off", !fertOn);
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

async function loadZoneMetrics() {
  try {
    const data = await fetchJson(`/api/latest?zone_id=${currentZone}`);
    sensorTimestampEl.textContent = data.timestamp || "--";
    renderMetrics(data.metrics || {});
    valveHintEl.textContent = `${zoneText(currentZone)} 数据已更新，可根据策略进行阀门控制。`;
  } catch (err) {
    sensorTimestampEl.textContent = "读取失败";
    renderMetrics({});
    valveHintEl.textContent = `数据读取失败：${err.message}`;
  }
}

function initValveToggle() {
  waterValveBtn.addEventListener("click", () => {
    valveStateByZone[currentZone].water = !valveStateByZone[currentZone].water;
    renderValveState();
  });

  fertValveBtn.addEventListener("click", () => {
    valveStateByZone[currentZone].fertilizer = !valveStateByZone[currentZone].fertilizer;
    renderValveState();
  });
}

function initSidebar() {
  const collapseBtn = document.getElementById("collapseBtn");
  collapseBtn?.addEventListener("click", () => {
    appShell.classList.toggle("sidebar-collapsed");
  });
}

async function bootstrap() {
  initSidebar();
  initValveToggle();
  renderZoneButtons();
  renderValveState();
  await loadZoneMetrics();
}

bootstrap();
