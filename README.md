# 红橙果园系统架构说明

## 1. 项目概览
本项目是一个“采集 + 预测 + 可视化 + 管理登录”的完整系统，核心包含四条链路：
- MQTT 实时采集传感器数据并入库。
- 预测服务按整点读取历史数据与天气数据，生成未来 24 小时预测。
- FastAPI 提供页面路由和数据接口。
- 前端大屏展示实时数据、预测数据、区域切换和智能诊断入口。

## 2. 架构分层
### 2.1 后端分层
- 路由层：负责 HTTP 接口、页面入口、参数校验、会话校验。
- 服务层：负责数据库访问、认证逻辑、MQTT 订阅逻辑、业务聚合。
- 启动入口：负责依赖装配、服务初始化、生命周期管理。

### 2.2 目录结构
- backend: FastAPI 后端代码（路由层 + 服务层 + 启动入口 + 运维脚本）
- web: 前端页面与样式脚本
- best_model&scaler: 预测模型与标准化器
- 图集: YOLO 占位图片数据
- 文档类文件: mysql.md、天气api.md、dify.md、完成.md

## 3. 全量目录与文件作用
以下仅列出当前业务相关文件（不含 .git、.venv、__pycache__）。

### 3.1 根目录文件
- ./.gitignore
  - Git 忽略规则，避免上传虚拟环境、缓存和图集目录等。

- ./README.md
  - 当前架构与目录说明文档。

- ./requirements.txt
  - Python 依赖清单（FastAPI、Uvicorn、PyMySQL、Paho-MQTT、Torch、Scikit-learn 等）。

- ./mysql.md
  - MySQL 相关配置与使用说明。

- ./天气api.md
  - 天气接口相关说明。

- ./dify.md
  - Dify 连接与内网映射说明。

- ./完成.md
  - 历史开发交付总结。

### 3.2 backend 目录
- ./backend/__init__.py
  - 后端包标识文件。

- ./backend/main.py
  - FastAPI 启动入口。
  - 负责挂载静态资源路径 /assets 与 /gallery。
  - 负责装配路由层与服务层。
  - 负责启动时连接数据库、建表检查、启动 MQTT；关闭时释放资源。

- ./backend/predictions.py
  - 预测服务主程序（独立进程）。
  - 按整点执行预测，写入 predictions 表。

- ./backend/create_admin.py
  - 管理员账号手动创建/重置脚本（无注册入口）。

- ./backend/create_mqtt_test_table.sql
  - 数据库建表 SQL（Real / predictions 相关）。

#### backend/routes（路由层）
- ./backend/routes/__init__.py
  - 路由包标识文件。

- ./backend/routes/basic_routes.py
  - 页面路由：/、/admin、/diagnosis、/health。
  - 页面访问时会做登录态检查（未登录跳转 /login）。

- ./backend/routes/auth_routes.py
  - 认证路由：/login、/auth/login、/auth/logout。

- ./backend/routes/api_routes.py
  - 数据路由：
    - /api/zones
    - /api/latest
    - /api/predictions
    - /api/yolo-placeholder
    - /api/overview
  - 路由层负责参数校验与权限检查，实际业务调用服务层完成。

#### backend/services（服务层）
- ./backend/services/__init__.py
  - 服务包标识文件。

- ./backend/services/db_utils.py
  - 数据库连接、通用锁、SQL 标识符处理工具。

- ./backend/services/data_service.py
  - 核心数据服务：
    - 传感器数据写入
    - 最新数据查询
    - 预测数据查询
    - 区域卡片数据构建
    - YOLO 数据构建

- ./backend/services/mqtt_service.py
  - MQTT 订阅服务：
    - 连接 broker
    - 订阅 6 个区域主题
    - 收到消息后解析并写入数据库

- ./backend/services/auth_service.py
  - 认证服务：
    - admin_users 表初始化
    - 密码哈希与校验
    - 登录校验
    - 管理员账号创建/更新

### 3.3 web 目录（前端）
- ./web/index.html
  - 大屏主页结构（左传感器、中区域+YOLO、右预测图）。

- ./web/app.js
  - 前端数据逻辑：
    - 拉取 API
    - 渲染 ECharts
    - 区域切换
    - YOLO 列表渲染
    - 会话失效时 401 自动跳转登录

- ./web/styles.css
  - 全局科技风样式与布局。

- ./web/login.html
  - 管理员登录页（无注册）。

- ./web/admin.html
  - 管理后台页面（Dify 地址、系统信息）。

- ./web/diagnosis.html
  - 智能诊断页面（嵌入 Dify Chatflow）。

### 3.4 模型与资源目录
- ./best_model&scaler/best_model.pth
  - 预测模型权重文件。

- ./best_model&scaler/x1_scaler.pkl
- ./best_model&scaler/x2_scaler.pkl
- ./best_model&scaler/y_scaler.pkl
  - 模型输入输出标准化器。

- ./lstm训练文件/train.py
  - 模型训练脚本。

- ./lstm训练文件/说明.md
  - 训练说明。

- ./图集/*.jpg / *.jpeg
  - YOLO 占位展示图片素材。

## 4. 关键访问路径
- 登录页: /login
- 大屏首页: /
- 管理后台: /admin
- 智能诊断: /diagnosis
- 健康检查: /health
- API 前缀: /api/*
- 静态资源: /assets/*
- 图集资源: /gallery/*

## 5. 运行流程（简版）
1. 用户访问页面，先通过会话校验。
2. 前端页面加载后调用 /api 接口拉数据。
3. MQTT 服务持续把采集数据写入 Real 表。
4. 预测服务按小时更新 predictions 表。
5. 前端展示实时与预测数据。

## 6. MQTT 订阅需要路由吗？
结论：不需要。

原因：
- MQTT 订阅是消息中间件连接行为，不是 HTTP 请求。
- 它在服务层中由 mqtt_service.py 直接连接 broker 并处理消息。
- 路由层只处理浏览器或客户端发来的 HTTP 请求。

你可以理解为：
- MQTT 走消息通道（订阅主题）。
- FastAPI 路由走 HTTP 通道（页面和 API）。

二者各司其职，不应混在同一层。

## 7. 管理员账号策略
- 不开放注册页面。
- 只允许管理员通过脚本手动创建或重置账号。
- 使用方式：
  - .venv/bin/python backend/create_admin.py --email 管理员邮箱 --username 管理员名 --password 管理员密码

## 8. 后续建议
- 增加 README 的部署章节（systemd、Nginx、备份策略）。
- 增加 API 文档章节（字段说明与示例返回）。
- 增加测试章节（接口健康检查、登录流程测试脚本）。
