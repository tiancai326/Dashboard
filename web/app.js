const metricConfig = [
  { key: "air_temp", label: "空温", unit: "℃", max: 40 },
  { key: "air_humidity", label: "空湿", unit: "%", max: 100 },
  { key: "light_intensity", label: "光照", unit: "Lux", max: 100000 },
  { key: "soil_temp", label: "土温", unit: "℃", max: 45 },
  { key: "soil_humidity", label: "土湿", unit: "%", max: 100 },
  { key: "ec", label: "EC", unit: "mS/cm", max: 4 },
  { key: "ph", label: "pH", unit: "", max: 14 },
  { key: "n", label: "氮", unit: "mg/kg", max: 450 },
  { key: "p", label: "磷", unit: "mg/kg", max: 180 },
  { key: "k", label: "钾", unit: "mg/kg", max: 650 },
];

let currentZone = "zone_1";
let radarChart;
let predictChart;

const metricListEl = document.getElementById("metricList");
const latestTimestampEl = document.getElementById("latestTimestamp");
const predictionHintEl = document.getElementById("predictionHint");
const yoloTableEl = document.getElementById("yoloTable");
const quickKpiEl = document.getElementById("quickKpi");
const appShell = document.getElementById("appShell");

function getNum(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "--";
  return Number(v).toFixed(digits);
}

function zoneTitle(zoneId) {
  const idx = Number(String(zoneId).replace("zone_", ""));
  return `区域 ${idx}`;
}

function initSidebar() {
  const btn = document.getElementById("collapseBtn");
  btn.addEventListener("click", () => {
    appShell.classList.toggle("sidebar-collapsed");
    setTimeout(() => {
      radarChart?.resize();
      predictChart?.resize();
    }, 260);
  });
}

function initZoneSelector() {
  const groups = document.querySelectorAll(".zone-group");
  groups.forEach((g) => {
    g.addEventListener("click", async () => {
      currentZone = g.dataset.zone;
      groups.forEach((x) => x.classList.remove("is-active"));
      g.classList.add("is-active");
      await loadZoneData();
    });
  });
  const defaultGroup = document.querySelector('.zone-group[data-zone="zone_1"]');
  defaultGroup?.classList.add("is-active");
}

function initCharts() {
  radarChart = echarts.init(document.getElementById("sensorRadarChart"));
  predictChart = echarts.init(document.getElementById("predictChart"));
  window.addEventListener("resize", () => {
    radarChart.resize();
    predictChart.resize();
  });
}

function renderMetrics(metrics = {}) {
  metricListEl.innerHTML = metricConfig
    .map((m) => {
      const digits = ["light_intensity", "n", "p", "k"].includes(m.key) ? 0 : 2;
      return `
        <div class="metric-card">
          <div class="metric-name">${m.label}</div>
          <div class="metric-value">${getNum(metrics[m.key], digits)}<span class="metric-unit">${m.unit}</span></div>
        </div>
      `;
    })
    .join("");

  const radarValues = metricConfig.map((m) => {
    const raw = Number(metrics[m.key] ?? 0);
    if (!Number.isFinite(raw)) return 0;
    return Math.min(100, (raw / m.max) * 100);
  });

  radarChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    radar: {
      center: ["50%", "53%"],
      radius: "67%",
      splitNumber: 5,
      indicator: metricConfig.map((m) => ({ name: m.label, max: 100 })),
      axisName: { color: "#9ed7ff", fontSize: 12 },
      splitLine: { lineStyle: { color: ["rgba(55,130,230,.25)"] } },
      splitArea: { areaStyle: { color: ["rgba(11,46,110,.18)", "rgba(9,34,88,.26)"] } },
      axisLine: { lineStyle: { color: "rgba(61, 176, 255, .5)" } },
    },
    series: [
      {
        type: "radar",
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { color: "#38f3ff", width: 2 },
        areaStyle: { color: "rgba(39,214,255,.32)" },
        itemStyle: { color: "#7dfaff" },
        data: [{ value: radarValues, name: zoneTitle(currentZone) }],
      },
    ],
  });
}

function renderYolo(records = [], errorMsg = "") {
  const fallbackRows = [
    {
      capture_time: "2026-04-13 10:22:15",
      zone_id: "Zone_3",
      result: "潜叶蛾",
      confidence: 0.92,
      level: "严重虫害",
    },
    {
      capture_time: "2026-04-13 10:18:42",
      zone_id: "Zone_2",
      result: "叶片黄化",
      confidence: 0.85,
      level: "轻度病害",
    },
    {
      capture_time: "2026-04-13 10:15:30",
      zone_id: "Zone_5",
      result: "健康叶片",
      confidence: 0.98,
      level: "果树健康",
    },
    {
      capture_time: "2026-04-13 10:12:18",
      zone_id: "Zone_1",
      result: "健康叶片",
      confidence: 0.97,
      level: "果树健康",
    },
    {
      capture_time: "2026-04-13 10:08:55",
      zone_id: "Zone_4",
      result: "健康叶片",
      confidence: 0.99,
      level: "果树健康",
    },
  ];

  const normalizeSeverity = (text = "") => {
    if (/(严重|虫害|病害|蛾|霉|腐)/.test(text)) return "danger";
    if (/(轻度|预警|黄化|疑似|异常)/.test(text)) return "warn";
    return "good";
  };

  const normalizeResult = (raw = "") => {
    if (!raw) return "健康叶片";
    if (/(healthy|normal|ok|健康)/i.test(raw)) return "健康叶片";
    if (/(yellow|黄化)/i.test(raw)) return "叶片黄化";
    if (/(leaf.*miner|潜叶|蛾)/i.test(raw)) return "潜叶蛾";
    return raw;
  };

  const buildRow = (r, idx) => {
    const captureTime = r?.capture_time || fallbackRows[idx].capture_time;
    const zone = r?.zone_id || fallbackRows[idx].zone_id;
    const result = normalizeResult(r?.result || fallbackRows[idx].result);
    const confidenceRaw = Number(r?.confidence ?? fallbackRows[idx].confidence);
    const confidenceText = Number.isFinite(confidenceRaw)
      ? `${Math.round(confidenceRaw * 100)}%`
      : `${Math.round(fallbackRows[idx].confidence * 100)}%`;
    const level = r?.level || fallbackRows[idx].level;
    const severity = normalizeSeverity(`${result} ${level}`);

    return { captureTime, zone, result, confidenceText, level, severity };
  };

  const baseRows = records.length
    ? records.slice(0, 5).map((r, idx) => buildRow(r, idx))
    : fallbackRows.map((r, idx) => buildRow(r, idx));

  if (errorMsg && baseRows[0]) {
    baseRows[0].result = "读取失败";
    baseRows[0].level = "接口异常";
    baseRows[0].severity = "warn";
  }

  yoloTableEl.innerHTML = baseRows
    .map(
      (row) => `
        <div class="monitor-row ${row.severity}">
          <div class="monitor-time">${row.captureTime}</div>
          <div class="monitor-zone">${row.zone}</div>
          <div class="monitor-result">${row.result}</div>
          <div class="monitor-conf">${row.confidenceText}</div>
          <div class="monitor-tag">${row.level}</div>
        </div>
      `
    )
    .join("");

  yoloTableEl.innerHTML = `
    <div class="monitor-head">
      <div>时间</div>
      <div>区域</div>
      <div>情况</div>
      <div>置信度</div>
      <div></div>
    </div>
    ${yoloTableEl.innerHTML}
  `;
}

function renderPrediction(rows = []) {
  if (!rows.length) {
    predictionHintEl.textContent = `${zoneTitle(currentZone)} 暂无预测数据`;
    predictChart.clear();
    quickKpiEl.innerHTML = "";
    return;
  }

  predictionHintEl.textContent = `${zoneTitle(currentZone)} / 共 ${rows.length} 小时`;

  const xAxis = rows.map((r) => r.predict_time.slice(5, 16));
  const soilTemp = rows.map((r) => Number(r.soil_temp_pred));
  const soilHum = rows.map((r) => Number(r.soil_humidity_pred));
  const ec = rows.map((r) => Number(r.ec_pred));
  const weatherTemp = rows.map((r) => Number(r.weather_temp ?? 0));
  const weatherHum = rows.map((r) => Number(r.weather_humidity ?? 0));

  predictChart.setOption({
    backgroundColor: "transparent",
    legend: {
      top: 8,
      textStyle: { color: "#9dcfff" },
      data: ["土温", "土湿", "EC", "天气温度", "天气湿度"],
    },
    grid: { left: 68, right: 78, top: 52, bottom: 30 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: xAxis,
      axisLine: { lineStyle: { color: "#5f9ad2" } },
      axisLabel: { color: "#98c7f0", rotate: 45 },
    },
    yAxis: [
      {
        type: "value",
        name: "土壤/EC",
        nameLocation: "middle",
        nameRotate: 90,
        nameGap: 50,
        nameTextStyle: { color: "#7fb5e2", fontSize: 12 },
        axisLine: { lineStyle: { color: "#68bbff" } },
        splitLine: { lineStyle: { color: "rgba(89,150,221,.16)" } },
        axisLabel: { color: "#96c9f3", margin: 10 },
      },
      {
        type: "value",
        name: "天气",
        nameLocation: "middle",
        nameRotate: -90,
        nameGap: 52,
        nameTextStyle: { color: "#78dfc3", fontSize: 12 },
        axisLine: { lineStyle: { color: "#60ffd2" } },
        splitLine: { show: false },
        axisLabel: { color: "#84e9ca", margin: 10 },
      },
    ],
    series: [
      { name: "土温", type: "line", smooth: true, data: soilTemp, symbol: "none", color: "#4cb8ff", lineStyle: { width: 2, color: "#4cb8ff" } },
      { name: "土湿", type: "line", smooth: true, data: soilHum, symbol: "none", color: "#7dd36a", lineStyle: { width: 2, color: "#7dd36a" } },
      { name: "EC", type: "line", smooth: true, data: ec, symbol: "none", color: "#f5d15f", lineStyle: { width: 2, color: "#f5d15f" } },
      { name: "天气温度", type: "line", smooth: true, yAxisIndex: 1, data: weatherTemp, symbol: "none", color: "#ff7b7b", lineStyle: { width: 2, color: "#ff7b7b" } },
      { name: "天气湿度", type: "line", smooth: true, yAxisIndex: 1, data: weatherHum, symbol: "none", color: "#67d8ff", lineStyle: { width: 2, color: "#67d8ff" } },
    ],
  });

  quickKpiEl.innerHTML = `
    <div class="kpi-card"><div class="kpi-title">未来24h土温均值</div><div class="kpi-value">${getNum(avg(soilTemp), 1)}℃</div></div>
    <div class="kpi-card"><div class="kpi-title">未来24h土湿均值</div><div class="kpi-value">${getNum(avg(soilHum), 1)}%</div></div>
    <div class="kpi-card"><div class="kpi-title">未来24h最大EC</div><div class="kpi-value">${getNum(Math.max(...ec), 2)}</div></div>
    <div class="kpi-card"><div class="kpi-title">天气湿度均值</div><div class="kpi-value">${getNum(avg(weatherHum), 1)}%</div></div>
  `;
}

function avg(arr) {
  if (!arr.length) return 0;
  return arr.reduce((s, x) => s + Number(x || 0), 0) / arr.length;
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

async function loadZoneData() {
  try {
    const [latest, pred] = await Promise.all([
      fetchJson(`/api/latest?zone_id=${currentZone}`),
      fetchJson(`/api/predictions?zone_id=${currentZone}&limit=24`),
    ]);

    latestTimestampEl.textContent = `${zoneTitle(currentZone)} / ${latest.timestamp}`;
    renderMetrics(latest.metrics || {});
    renderPrediction(pred.rows || []);
  } catch (err) {
    latestTimestampEl.textContent = `数据读取失败: ${err.message}`;
  }
}

async function loadStaticPanels() {
  try {
    const yoloRes = await fetchJson("/api/yolo-placeholder?limit=5");
    renderYolo(yoloRes.records || []);
  } catch (err) {
    renderYolo([], `读取失败: ${err.message}`);
  }
}

async function bootstrap() {
  initSidebar();
  initZoneSelector();
  initCharts();
  await loadStaticPanels();
  await loadZoneData();
  setInterval(loadZoneData, 60 * 1000);
  setInterval(loadStaticPanels, 3 * 60 * 1000);
}

bootstrap();
