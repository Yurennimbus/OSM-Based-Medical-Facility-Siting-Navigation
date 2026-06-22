# WebGIS — 医疗设施选址与导航系统
# Medical Facility Site Selection & Navigation System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue-3.4-4FC08D.svg)](https://vuejs.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900.svg)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 中文说明

### 项目简介

基于 **FastAPI + Vue3 + Leaflet + NetworkX** 的通用 WebGIS 平台。支持多城市医疗设施空间选址分析（MCDA）与容量感知路径导航。采用数据无关设计——用户只需替换数据配置即可切换任意城市。

### 功能特性

**选址分析**
- 基于网格的多准则决策分析（MCDA），综合四项因子：人口密度（W1）、交通可达性（W2）、竞争回避（W3）、用地适宜性（W4）
- 实时滑块调节权重，即时触发热力图重算
- Top 5 推荐选址网格高亮标注

**路径导航**
- 基于 A\* 算法的道路网络最短路径计算
- 容量感知综合评分：`综合 = 距离 - α × 能力评分`
- 两种导航模式：最近设施自动查找 / 指定设施导航
- 返回至多 3 条候选路径供对比

**数据管理**
- `config.yaml` 驱动：新增城市只需编辑配置文件
- 支持 GeoJSON / Shapefile / CSV / GeoPackage 多格式导入
- WebUI 动态导入 + 字段自动映射（中英文字段名）
- 设施诊疗能力评分可在线编辑

**地图交互**
- 默认浅灰背景（无底图模式），可切换至天地图底图（需 API Key）
- 基础显示图层：用地（面）、道路（线）、边界（面，自动检测多边形数据）
- 医疗设施 MarkerCluster 聚合（缩放 ≥16 级展开全部）
- 铁路站点 MarkerCluster 聚合 + 点击弹窗显示站名
- 设施分类勾选框：医院 / 诊所 / 药店 / 其他，独立控制地图显隐
- 属性表面板：搜索、分类筛选、按名称/类型/能力值排序、分页
- 点击设施查看详情，一键导航

### 系统架构

```
Prj_1/
├── config.yaml              # 城市数据配置
├── run.py                   # Web 服务启动入口
├── run_server.py            # 无浏览器启动入口
├── init.py                  # 数据初始化
├── start.bat                # Windows 快速启动
├── reset.bat                # 系统重置还原
├── requirements.txt         # Python 依赖
├── README.md                # 项目说明 (本文件)
├── USER_GUIDE.md            # 用户操作手册
├── LICENSE                  # MIT 协议
├── .gitignore
├── backend/
│   ├── config.py            # 配置读取模块
│   ├── database.py          # SQLite 城市注册 + 设施容量表
│   ├── importer.py          # 多格式数据导入器 + 字段自动映射
│   ├── suitability.py       # 网格 MCDA 分析引擎
│   ├── routing.py           # A* 路由引擎（NetworkX）
│   ├── models.py            # Pydantic 数据模型
│   └── main.py              # FastAPI 应用入口
└── frontend/
    └── index.html           # Vue3 + Leaflet 单页应用
```

### 快速开始

**环境要求**: Python ≥ 3.10，网络连接（加载 Leaflet/Vue CDN）
> ⚠ 系统默认无底图。如需底图，选择天地图并在官网申请 API Key。

```bash
# 1. 克隆仓库
git clone <repo-url>
cd <部署的文件夹位置>

# 2. 创建虚拟环境 (推荐)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt

# 4. 准备数据
#    将城市 GeoJSON/Shapefile 数据放入 Data/<city_name>/ 目录
#    在 config.yaml 中配置城市信息（参考示例模板）

# 5. 初始化并启动
python init.py
python run.py
```

浏览器自动打开 → `http://localhost:8000`。按 `Ctrl+C` 停止。

**也可以直接双击 start.bat 启动，自动打开网页后，在页面上方选择你要导入文件的目录，系统会自动扫描识别。**

### 自定义城市数据

**必需图层**（缺一不可）：

| 图层 | 几何类型 | 关键字段 | 说明 |
|---|---|---|---|
| `health` | Point | `category`, `name`, `attribute` | 医疗设施点（`attribute` 可选，为默认诊疗能力 0~1）|
| `landuse` | Polygon | `fclass`（需含 `residential`） | 土地利用面 |
| `roads` | LineString | `fclass` | 道路网络线 |

**可选图层**：`population`（人口分布点/面）、`railways`（铁路线）、`railway_stations`（火车站）、`boundary`（行政区划面，自动检测目录中的面要素数据）

**字段自动映射**：导入器自动识别以下字段名（大小写不敏感）——

| 用途 | 候选字段名 |
|---|---|
| 设施名称 | `name`, `facility_name`, `名称` |
| 设施分类 | `category`, `fclass`, `type`, `facility_type`, `类型` |
| 诊疗能力 | `attribute`, `capacity`, `能力` |
| 经度 | `wgs_lng`, `longitude`, `lon`, `lng`, `经度` |
| 纬度 | `wgs_lat`, `latitude`, `lat`, `纬度` |

**支持格式**: `.geojson` `.json` `.shp` `.gpkg` `.csv`

> 诊疗能力自动读取 `attribute` 字段；若名称含"建设中"则强制为 0。可在 WebUI 容量管理中在线修改。

### 配置参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `grid.default_cell_size` | 0.005° | 网格单元大小（度） |
| `grid.max_cells` | 50000 | 最大网格数（防内存溢出） |
| `routing.snap_tolerance_m` | 2000m | 起点吸附道路容差 |
| `routing.max_candidates` | 30 | 最近设施搜索数量 |
| `routing.local_road_padding_deg` | 0.05° | 局部路网外扩范围 |

**容量权重 α**：0 = 仅距离 | 0.5 = 默认均衡 | 1 = 等权重 | 2 = 优先高容量

### 注意事项

1. 所有数据使用 WGS84 (EPSG:4326) 坐标系
2. Shapefile 默认 UTF-8 编码读取，如有乱码请转换编码
3. 大数据集（>5 万道路段）路由计算需 5-30 秒
4. `Data/` 和 `*.db` 已加入 `.gitignore`，请勿提交地理数据

---

## 📖 English Description

### Overview

A universal WebGIS platform based on **FastAPI + Vue3 + Leaflet + NetworkX** for multi-city medical facility spatial site selection analysis (MCDA) and capacity-aware route navigation. Data-agnostic design — users can switch between cities by simply replacing the data configuration.

### Features

**Suitability Analysis**
- Grid-based Multi-Criteria Decision Analysis (MCDA) with 4 weighted factors: Population Density (W1), Traffic Accessibility (W2), Competition Avoidance (W3), Land Use Suitability (W4)
- Real-time weight sliders trigger instant heatmap recalculation
- Top 5 recommended site grids highlighted on the map

**Route Navigation**
- A\* shortest-path algorithm on road network (via NetworkX)
- Capacity-aware composite scoring: `Composite = Distance - α × Capacity_Score`
- Two navigation modes: auto-find nearest facility / navigate to a user-selected facility
- Up to 3 candidate routes for comparison

**Data Management**
- `config.yaml` driven: add a new city by editing the config file
- Multi-format import support: GeoJSON, Shapefile, CSV, GeoPackage
- WebUI dynamic import with automatic field mapping (Chinese & English field names)
- Facility capacity scores editable online via WebUI

**Map Interaction**
- Default light-gray background (no-basemap mode); switchable to Tianditu basemap (API key required)
- Base display layers: Land Use (polygon), Roads (line), Boundary (polygon, auto-detected)
- MarkerCluster for health facilities (all shown at zoom ≥ 16)
- MarkerCluster for railway stations + click popup showing station name
- Facility category visibility toggles: Hospital / Clinic / Pharmacy / Other
- Attribute table panel: search, category filter, sort, pagination
- Click a facility for detail popup, one-click navigate

### Quick Start

**Prerequisites**: Python ≥ 3.10, internet connection (for Leaflet/Vue CDN)
> ⚠ Default is no basemap. For basemap, select Tianditu and apply for an API key.

```bash
# 1. Clone
git clone <repo-url>
cd <file>

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate     # Linux/macOS
# venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Prepare data
#    Place your city GeoJSON/Shapefile data under Data/<city_name>/
#    Configure the city in config.yaml (see template)

# 5. Initialize and start
python init.py
python run.py
```

Browser opens → `http://localhost:8000`. Press `Ctrl+C` to stop.

**You can also double-click start.bat to start it directly. After automatically opening the webpage, select the directory where you want to import the file at the top of the page, and the system will automatically scan and recognize it. **

### Custom City Data

**Required Layers** (all three must be present):

| Layer | Geometry Type | Key Fields | Description |
|---|---|---|---|
| `health` | Point | `category`, `name`, `attribute` | Medical facilities (`attribute` optional, default capacity 0~1) |
| `landuse` | Polygon | `fclass` (must include `residential`) | Land use polygons |
| `roads` | LineString | `fclass` | Road network |

**Optional Layers**: `population`, `railways`, `railway_stations`, `boundary` (administrative boundary polygon, auto-detected from directory)

**Auto Field Mapping**: The importer automatically detects these field names (case-insensitive):

| Purpose | Candidate Field Names |
|---|---|
| Facility Name | `name`, `facility_name`, `名称` |
| Category | `category`, `fclass`, `type`, `facility_type`, `类型` |
| Capacity Score | `attribute`, `capacity`, `能力` |
| Longitude | `wgs_lng`, `longitude`, `lon`, `lng`, `经度` |
| Latitude | `wgs_lat`, `latitude`, `lat`, `纬度` |

**Supported Formats**: `.geojson` `.json` `.shp` `.gpkg` `.csv`

### Notes

1. All data must use WGS84 (EPSG:4326) CRS
2. Shapefile encoding defaults to UTF-8; convert if garbled
3. Large datasets (>50K road segments) may need 5-30s for routing
4.  `Data/` and `*.db` are gitignored — do not commit geographic data

---

## 📡 API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/cities` | List all active cities |
| `GET` | `/api/cities/{schema}` | Get city detail |
| `POST` | `/api/cities/scan` | Scan directory for layers |
| `POST` | `/api/cities/import-dynamic` | Import city from directory |
| `POST` | `/api/cities/reload` | Reload all configured cities |
| `POST` | `/api/analyze/suitability` | Run suitability analysis |
| `POST` | `/api/routing/navigate` | Find nearest facilities |
| `POST` | `/api/routing/navigate-to` | Navigate to specific facility |
| `PUT` | `/api/facilities/capacity` | Update facility capacity score |
| `GET` | `/api/facilities/{schema}` | List all facility capacities |
| `GET` | `/api/layers/{schema}/{layer}` | Get layer GeoJSON data |
| `GET` | `/api/layers/{schema}/list` | List layer metadata |
| `GET` | `/api/health/{schema}/{lon}/{lat}` | Facility detail by coordinates |

---

## 📖 用户手册 / User Guide

详见 [USER_GUIDE.md](USER_GUIDE.md) — 包含完整的中文和英文操作指南。

See [USER_GUIDE.md](USER_GUIDE.md) for complete guidance in both Chinese and English.

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)
