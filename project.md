


这是一个非常标准且极其专业的**“软硬件并行开发”**策略！

在真实的大厂物联网项目开发中，软件团队绝对不会干等着硬件团队把板子焊好才开始写代码。工业界的标准做法就是你说的这种：**“数据模拟（Mock Data）与桩代码测试”**。

针对你的现状，我为你制定了从**中间件选型**到**Python高仿真模拟脚本**的完整落地方案：

---

### 一、 MQTT Broker 推荐：毫不犹豫选 Mosquitto！

对于你们目前打比赛、部署在云服务器上的场景，我强烈推荐使用 **Eclipse Mosquitto**。

*   **为什么不选 EMQX？** EMQX 适合千万级并发的企业集群，对服务器内存要求高，你们用起来太重了。
*   **为什么选 Mosquitto？** 它是全球物联网界最经典、最轻量级的开源 MQTT 服务器。**占用内存极小（几 MB）**，性能极速，且在 Linux (Ubuntu/CentOS) 上安装只需要一行命令，基本属于“零配置开箱即用”。

**👉 极速安装命令（假设你们用的是 Ubuntu 云服务器）：**
```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto  # 设置开机自启
sudo systemctl start mosquitto   # 启动服务
```
*(装完之后，你的服务器 1883 端口就已经随时待命，准备接收数据了！)*

---

### 二、 高仿真 Python 模拟脚本（核心大招）

为了让你的大屏展示和 Dify Agent 测试达到最逼真的效果，这个脚本不能只是简单地 `random` 生成随机数。

我严格按照你发给我的**论文 PDF 里的“最优范围”和“危险警报线”**，为你写了这个脚本。它具备以下高级特性：
1.  **昼夜节律联动：** 白天有光照、温度高、水分掉得快；晚上没光照、温度低。（极其逼真！）
2.  **受控的异常触发：** 有 10% 的概率会突然生成一个“极端异常值”（比如水分暴跌到 12%，或者 EC 值飙升），**专门用来触发你的前端大屏红色报警和 Dify 智能体下发工单！**
3.  **多区域并发：** 一次性遍历生成 Zone_1 到 Zone_6 的数据并发送。

**👉 将以下代码保存为 `mock_sensor.py` 在你的服务器或本地运行：**

import paho.mqtt.client as mqtt
import time
import json
import random
import math
from datetime import datetime

# ================= 配置区 =================
MQTT_BROKER = "127.0.0.1"  
MQTT_PORT = 1883
TOPIC_PREFIX = "orchard/sensor/"
ZONES =["Zone_1", "Zone_2", "Zone_3", "Zone_4", "Zone_5", "Zone_6"]

def get_global_weather():
    """
    [天空层]：全园共享的 1 套气象基准数据
    """
    current_hour = datetime.now().hour
    is_daytime = 6 <= current_hour <= 18
    
    if is_daytime:
        air_temp = round(random.uniform(25.0, 32.0), 1)
        air_humidity = round(random.uniform(60.0, 75.0), 1)
        
        # 完美的抛物线光照模拟
        time_fraction = (current_hour - 6) / 12.0 
        peak_light = random.uniform(80000, 100000) 
        light = int(peak_light * math.sin(time_fraction * math.pi))
        
        # 云层遮挡波动
        if random.random() < 0.2: 
            light = int(light * 0.6) 
    else:
        air_temp = round(random.uniform(15.0, 22.0), 1) 
        air_humidity = round(random.uniform(75.0, 95.0), 1) 
        light = 0 # 晚上没太阳
        
    return air_temp, air_humidity, light

def get_zone_soil_data(zone_id):
    """
    [地下层]：各个轮灌区独立的 N 套土壤数据 (加入真实 NPK 灾害模型)
    """
    # 1. 基础健康状态 (最优范围)
    soil_humidity = round(random.uniform(60.0, 80.0), 1)
    soil_temp = round(random.uniform(17.0, 26.0), 1)
    ec = round(random.uniform(0.5, 1.5), 2)
    ph = round(random.uniform(5.5, 6.5), 1)
    n = round(random.uniform(80, 150), 1)
    p = round(random.uniform(30, 40), 1)
    k = round(random.uniform(100, 250), 1)
    
    # 2. 🌟 制造高级“受控灾害” (总概率控制在 15% 左右，用于演示 AI 报警)
    anomaly_chance = random.random()
    
    if anomaly_chance < 0.04:
        # 【灾害 1：极度干旱】 (概率 4%)
        soil_humidity = round(random.uniform(30.0, 45.0), 1) 
        print(f"[⚠️旱灾警报] {zone_id} 极度干旱！水分仅 {soil_humidity}%")
        
    elif 0.04 <= anomaly_chance < 0.08:
        # 【灾害 2：暴雨淋溶 / 严重脱肥】 (概率 4%)
        soil_humidity = round(random.uniform(85.0, 95.0), 1) # 暴雨导致积水饱和
        ec = round(random.uniform(0.1, 0.3), 2)              # 肥料被冲走，EC暴跌
        n = round(random.uniform(10.0, 39.0), 1)             # 缺氮 (<40)
        p = round(random.uniform(5.0, 14.0), 1)              # 缺磷 (<15)
        k = round(random.uniform(10.0, 49.0), 1)             # 缺钾 (<50)
        print(f"[🚨脱肥警报] {zone_id} 遭暴雨淋溶！EC骤降至 {ec}，N/P/K全面流失极低！")
        
    elif 0.08 <= anomaly_chance < 0.12:
        # 【灾害 3：盲目施肥 / 盐害烧根】 (概率 4%)
        ec = round(random.uniform(2.0, 3.5), 2)              # 施肥过多，EC飙升
        n = round(random.uniform(251.0, 400.0), 1)           # 氮过剩 (>250) 易徒长
        p = round(random.uniform(81.0, 150.0), 1)            # 磷过剩 (>80) 易板结
        k = round(random.uniform(401.0, 600.0), 1)           # 钾过剩 (>400) 粗皮大果
        print(f"  [☣️肥害警报] {zone_id} 盲目施肥导致烧根！EC飙升至 {ec}，N/P/K严重超标！")
        
    elif 0.12 <= anomaly_chance < 0.15:
        # 【灾害 4：夏季高温闷根】 (概率 3%)
        soil_temp = round(random.uniform(32.0, 36.0), 1)
        print(f"  [🔥高温警报] {zone_id} 遭遇极端高温！土温达 {soil_temp}℃")

    return soil_temp, soil_humidity, n, p, k, ph, ec

def main():
    client = mqtt.Client("Mock_Sensor_Device")
    print(f"正在连接 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("✅ 连接成功！开始模拟发送传感器数据...\n")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    client.loop_start()

    try:
        while True:
            current_timeStr = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"========== 发送批次: {current_timeStr} ==========")
            
            air_temp, air_humidity, light = get_global_weather()
            print(f"🌤️ 全局气象抓取 -> 空温:{air_temp}℃, 空湿:{air_humidity}%, 光照:{light}Lux")
            
            for zone in ZONES:
                soil_temp, soil_humidity, n, p, k, ph, ec = get_zone_soil_data(zone)
                
                payload_dict = {
                    "zone_id": zone,
                    "soil_temp": soil_temp,
                    "soil_humidity": soil_humidity,
                    "n": n,
                    "p": p,
                    "k": k,
                    "ph": ph,
                    "ec": ec,
                    "air_temp": air_temp,         
                    "air_humidity": air_humidity, 
                    "light_intensity": light      
                }
                
                payload_json = json.dumps(payload_dict)
                topic = f"{TOPIC_PREFIX}{zone}"
                
                client.publish(topic, payload_json)
                print(f"  📤 发送至 {topic}")
            
            print("====================================================\n")
            time.sleep(3600) # 模拟每一个小时发送一次
            
    except KeyboardInterrupt:
        print("\n停止模拟发送。")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()

---

### 三、 接下来你们后端的动作（打通闭环）

有了这个不断往外吐数据的 Python 脚本，你们后端和前端的同学就完全不需要等硬件了！

1. **后端（FastAPI）同学的动作：**
   写一个后台进程，用 `paho-mqtt` 订阅 `orchard/sensor/+` 频道。收到上面脚本发来的 JSON 后，提取数据，加上当前的时间戳（向下取整对齐），直接 `INSERT` 进 MySQL 数据库。




二、 终极 MySQL 数据库表结构设计（可以直接建表了！）
为了完美承载这“地上 3 个全局气象 + 地下 7 个微环境”共 10 种数据，并且保证时序预测和图表查询极度顺滑。你们后端的同学需要建立下面这张名为 soil_sensor_data 的核心宽表。
这张表的设计堪称工业级典范，请直接抄作业：
字段名 (列名)	数据类型 (MySQL)	物理含义 / 备注	正常参考范围
id	BIGINT (自增主键)	数据的唯一流水号	无
timestamp	DATETIME (索引)	对齐到整点的时间戳 (如 2026-04-02 08:00:00)	无
zone_id	VARCHAR(20) (索引)	轮灌区编号 (如 Zone_1 ~ Zone_6)	Zone_1~Zone_6
air_temp	FLOAT	空气温度 (天空基准站，全园统一)	15.0 ~ 35.0 ℃
air_humidity	FLOAT	空气相对湿度 (天空基准站，全园统一)	50.0 ~ 95.0 %
light_intensity	INT	光照强度 (天空基准站，全园统一)	0 ~ 100,000 Lux
soil_temp	FLOAT	土壤温度 (各区独立)	17.0 ~ 26.0 ℃
soil_humidity	FLOAT	土壤相对含水量 (各区独立，触发灌溉的核心)	60.0 ~ 80.0 %
ec	FLOAT	土壤电导率 (各区独立，反映总肥力)	0.5 ~ 1.5 mS/cm
ph	FLOAT	土壤酸碱度 (各区独立)	5.5 ~ 6.5
n	FLOAT	土壤碱解氮 (各区独立)	80 ~ 150 mg/kg
p	FLOAT	土壤有效磷 (各区独立)	30 ~ 40 mg/kg
k	FLOAT	土壤速效钾 (各区独立)	100 ~ 250 mg/kg



当前已完成的事项如下：

已部署 MQTT Broker（Mosquitto），并完成启动、开机自启与可用性验证。
已实现模拟传感器发布脚本，包含 6 个分区、昼夜联动、异常注入、MQTT 发布逻辑，脚本在 mock_sensor.py。
已把发送策略从“固定间隔”改为“每个整点发送”（例如 09:00、10:00、11:00）。
已将服务器系统时区切换为 Asia/Shanghai（北京时间），不是仅脚本局部时区，因此后续其他服务默认也会使用北京时间。
已将模拟发送配置为 systemd 常驻服务，当前处于运行状态，并在日志中确认正在等待下一个整点触发发送。
继续使用 Autopilot

已完成你要求的总结交付：梳理了 Mosquitto 部署、模拟脚本实现、整点发送改造、服务器全局切换北京时间、以及 systemd 常驻运行这几项已落地结果。