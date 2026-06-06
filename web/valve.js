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
const waterCountdownTimers = {};
const waterCountdownRemaining = {};

const zoneSelectorEl = document.getElementById("zoneSelector");
const sensorTitleEl = document.getElementById("sensorTitle");
const sensorTimestampEl = document.getElementById("sensorTimestamp");
const sensorListEl = document.getElementById("sensorList");
const valveZoneTextEl = document.getElementById("valveZoneText");
const waterValveStatusEl = document.getElementById("waterValveStatus");
const fertValveStatusEl = document.getElementById("fertValveStatus");
const waterValveBtn = document.getElementById("waterValveBtn");
const fertValveBtn = document.getElementById("fertValveBtn");
const waterDurationHoursEl = document.getElementById("waterDurationHours");
const waterDurationMinutesEl = document.getElementById("waterDurationMinutes");
const waterDurationSecondsEl = document.getElementById("waterDurationSeconds");
const autoControlBtn = document.getElementById("autoControlBtn");
const autoControlText = document.getElementById("autoControlText");
const valveHintEl = document.getElementById("valveHint");
const valveModalEl = document.getElementById("valveModal");
const valveModalMessageEl = document.getElementById("valveModalMessage");
const autoModalEl = document.getElementById("autoModal");
const appShell = document.getElementById("appShell");

function showValveModal(message) {
  if (!valveModalEl || !valveModalMessageEl) return;
  valveModalMessageEl.textContent = message;
  valveModalEl.classList.add("is-visible");
  valveModalEl.setAttribute("aria-hidden", "false");
}

function hideValveModal() {
  if (!valveModalEl) return;
  valveModalEl.classList.remove("is-visible");
  valveModalEl.setAttribute("aria-hidden", "true");
}

function showAutoModal() {
  if (!autoModalEl) return;
  autoModalEl.classList.add("is-visible");
  autoModalEl.setAttribute("aria-hidden", "false");
}

function hideAutoModal() {
  if (!autoModalEl) return;
  autoModalEl.classList.remove("is-visible");
  autoModalEl.setAttribute("aria-hidden", "true");
}

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
    const countdownKey = `${currentZone}:${type}`;
    if (type === "water" && waterCountdownRemaining[countdownKey] !== undefined && isOn) {
      const remaining = waterCountdownRemaining[countdownKey];
      statusEl.textContent = `水阀已开启，倒计时 ${formatDuration(remaining)}`;
    } else if (valveSuccessTimers[successKey]) {
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

async function postJson(url, payload) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("not authenticated");
  }
  if (!resp.ok) throw new Error(`${url} -> ${resp.status}`);
  return resp.json();
}

async function fetchAck() {
  const resp = await fetch("/api/valve/ack");
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("not authenticated");
  }
  if (!resp.ok) throw new Error(`/api/valve/ack -> ${resp.status}`);
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

  autoControlBtn?.addEventListener("click", () => {
    showAutoModal();
  });
}

function renderAutoControl() {
  if (!autoControlBtn || !autoControlText) return;
  autoControlBtn.textContent = "开启全自动化管理";
  autoControlText.textContent = "如您想全自动化管理，请点击该按钮开启";
  autoControlBtn.disabled = false;
  autoControlBtn.classList.remove("is-active", "is-pending");
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatDuration(totalSeconds) {
  const sec = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(sec / 3600);
  const minutes = Math.floor((sec % 3600) / 60);
  const seconds = sec % 60;
  if (hours > 0) return `${hours}小时${minutes}分${seconds}秒`;
  if (minutes > 0) return `${minutes}分${seconds}秒`;
  return `${seconds}秒`;
}

function getWaterDurationSeconds() {
  const hours = Number(waterDurationHoursEl?.value || 0);
  const minutes = Number(waterDurationMinutesEl?.value || 0);
  const seconds = Number(waterDurationSecondsEl?.value || 0);
  const total = Math.max(0, hours * 3600 + minutes * 60 + seconds);
  return total;
}

function stopWaterCountdown(zone) {
  const key = `${zone}:water`;
  if (waterCountdownTimers[key]) {
    clearInterval(waterCountdownTimers[key]);
    delete waterCountdownTimers[key];
  }
  delete waterCountdownRemaining[key];
}

async function waitForAck(startEpochSeconds, timeoutMs = 12000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const data = await fetchAck();
    const ack = data?.ack;
    if (ack && ack.status === "ok" && ack.received_at && ack.received_at >= startEpochSeconds - 1) {
      return ack;
    }
    await wait(800);
  }
  return null;
}

async function autoCloseWaterValve(zone) {
  const sentAt = Date.now() / 1000;
  try {
    await postJson("/api/valve/drainage", {
      value: 0,
      zone_id: zone,
      source: "dashboard-auto",
    });
    const ack = await waitForAck(sentAt);
    if (!ack) {
      valveHintEl.textContent = "自动关闭未收到确认";
      showValveModal("自动关闭失败：未收到确认");
      return false;
    }
    return true;
  } catch (err) {
    valveHintEl.textContent = `自动关闭失败：${err.message}`;
    showValveModal(`自动关闭失败：${err.message}`);
    return false;
  }
}

function startWaterCountdown(zone, duration) {
  const key = `${zone}:water`;
  stopWaterCountdown(zone);
  waterCountdownRemaining[key] = duration;
  waterCountdownTimers[key] = setInterval(async () => {
    waterCountdownRemaining[key] -= 1;
    if (waterCountdownRemaining[key] <= 0) {
      stopWaterCountdown(zone);
      valvePendingByZone[zone].water = { targetOn: false };
      if (currentZone === zone) renderValveState();
      const closed = await autoCloseWaterValve(zone);
      delete valvePendingByZone[zone].water;
      if (closed) {
        valveStateByZone[zone].water = false;
        if (currentZone === zone) renderValveState();
      }
      return;
    }
    if (currentZone === zone) renderValveState();
  }, 1000);
  if (currentZone === zone) renderValveState();
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

  if (type === "water" && !targetOn) {
    stopWaterCountdown(zone);
  }

  valvePendingByZone[zone][type] = { targetOn };
  renderValveState();

  if (type === "water") {
    const duration = getWaterDurationSeconds();
    if (targetOn && duration <= 0) {
      delete valvePendingByZone[zone][type];
      valveHintEl.textContent = "请输入水阀开启时长（秒）";
      renderValveState();
      return;
    }
    try {
      const sentAt = Date.now() / 1000;
      await postJson("/api/valve/drainage", {
        value: targetOn ? 1 : 0,
        duration: targetOn ? duration : undefined,
        zone_id: zone,
        source: "dashboard",
      });
      const ack = await waitForAck(sentAt);
      if (!ack) {
        delete valvePendingByZone[zone][type];
        valveHintEl.textContent = "未收到水阀确认信号";
        showValveModal("水阀操作失败：未收到确认");
        renderValveState();
        return;
      }
    } catch (err) {
      delete valvePendingByZone[zone][type];
      valveHintEl.textContent = `排水命令发送失败：${err.message}`;
      showValveModal(`水阀操作失败：${err.message}`);
      renderValveState();
      return;
    }
  }

  valveStateByZone[zone][type] = targetOn;
  delete valvePendingByZone[zone][type];
  if (type === "water") {
    if (targetOn) {
      startWaterCountdown(zone, getWaterDurationSeconds());
    } else {
      stopWaterCountdown(zone);
    }
  }
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

function initValveModal() {
  if (!valveModalEl) return;
  valveModalEl.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.dataset.action === "close") {
      hideValveModal();
    }
  });
}

function initAutoModal() {
  if (!autoModalEl) return;
  autoModalEl.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.dataset.autoAction === "close") {
      hideAutoModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideAutoModal();
    }
  });
}

async function bootstrap() {
  initSidebar();
  initValveModal();
  initAutoModal();
  initValveToggle();
  renderZoneButtons();
  renderValveState();
  renderAutoControl();
  await loadZoneMetrics();
}

bootstrap();
