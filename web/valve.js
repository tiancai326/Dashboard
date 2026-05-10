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
const valvePendingByZone = {};
const valveSuccessTimers = {};

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
  const pending = valvePendingByZone[currentZone] || {};
  const waterOn = Boolean(state.water);
  const fertOn = Boolean(state.fertilizer);
  const zone = zoneText(currentZone);

  valveZoneTextEl.textContent = zone;

  renderSingleValve("water", waterOn, pending.water, waterValveStatusEl, waterValveBtn);
  renderSingleValve("fertilizer", fertOn, pending.fertilizer, fertValveStatusEl, fertValveBtn);
}

function renderSingleValve(type, isOn, pending, statusEl, btnEl) {
  const stateText = isOn ? "开启" : "关闭";
  const label = type === "water" ? "水阀" : "肥阀";

  if (pending) {
    statusEl.textContent = `${label}正在${pending.targetOn ? "开启" : "关闭"}，等待信号发送...`;
    btnEl.textContent = "发送中";
    btnEl.disabled = true;
  } else {
    const successKey = `${currentZone}:${type}`;
    if (valveSuccessTimers[successKey]) {
      statusEl.textContent = `发送成功，已${isOn ? "开启" : "关闭"}`;
    } else {
      statusEl.textContent = `当前状态：${isOn ? "开启" : "关闭"}`;
    }
    btnEl.textContent = stateText;
    btnEl.disabled = false;
  }

  setValveButtonClass(btnEl, isOn, Boolean(pending));
}

function setValveButtonClass(btnEl, isOn, isPending) {
  btnEl.classList.toggle("is-on", isOn);
  btnEl.classList.toggle("is-off", !isOn);
  btnEl.classList.toggle("is-pending", isPending);
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
  waterValveBtn.addEventListener("click", async () => {
    await toggleValve("water");
  });

  fertValveBtn.addEventListener("click", async () => {
    await toggleValve("fertilizer");
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function toggleValve(type) {
  const zone = currentZone;
  valveStateByZone[zone] ||= { water: false, fertilizer: false };
  valvePendingByZone[zone] ||= {};
  if (valvePendingByZone[zone][type]) return;

  const targetOn = !Boolean(valveStateByZone[zone][type]);
  const successKey = `${zone}:${type}`;
  if (valveSuccessTimers[successKey]) {
    clearTimeout(valveSuccessTimers[successKey]);
    delete valveSuccessTimers[successKey];
  }

  valvePendingByZone[zone][type] = { targetOn };
  renderValveState();

  await wait(2000);
  if (!valvePendingByZone[zone]?.[type]) return;
  await wait(2000);

  valveStateByZone[zone][type] = targetOn;
  delete valvePendingByZone[zone][type];
  valveSuccessTimers[successKey] = setTimeout(() => {
    delete valveSuccessTimers[successKey];
    if (currentZone === zone) renderValveState();
  }, 1800);

  if (currentZone === zone) renderValveState();
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
