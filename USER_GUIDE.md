# 用户操作手册 / User Guide

## 医疗设施选址与导航系统 / Medical Facility Site Selection & Navigation

---

# 中文操作手册

## 目录

1. [系统概述](#1-系统概述)
2. [界面布局](#2-界面布局)
3. [城市切换](#3-城市切换)
4. [选址分析](#4-选址分析)
5. [路径导航](#5-路径导航)
6. [设施属性表](#6-设施属性表)
7. [容量管理](#7-容量管理)
8. [数据导入](#8-数据导入)
9. [图层控制](#9-图层控制)
10. [常见问题](#10-常见问题)

---

## 1. 系统概述

本系统是一个 WebGIS 平台，用于医疗设施的**空间选址分析**和**路径导航**。系统采用数据无关设计，可通过替换数据配置切换不同城市。

### 核心概念

- **适宜性**：网格单元对医疗设施选址的综合适宜度评分（0~1），越高越适宜。
- **综合评分**：路径选择的综合评价指标：`距离 - α × 能力评分`。数值越低越优（距离短 + 能力高）。
- **诊疗能力**：设施的服务能力评分（0~10），由用户编辑，影响路径推荐优先级。

---

## 2. 界面布局

```
┌──────────────────────────────────────────────────────────┐
│  Top Bar: Title | City Selector | Import Button          │
├──────────────┬───────────────────────────────────────────┤
│  Left Panel  │         Map Area                          │
│  ┌────────┐  │                                           │
│  │Tabs:   │  │    ┌─ Basemap Selector  ──┐               │
│  │Suit/Nav│  │    │ Tianditu | None      │               │
│  │Fac/Cap │  │    └──────────────────────┘               │
│  └────────┘  │    ┌─ Layer Controls  ──┐                 │
│              │    │ Health|Land|Road   │                 │
│  Param Panel │    │ Rail|Heatmap|Clear │                 │
│  (dynamic)   │    └────────────────────┘                 │
│              │    ┌─ Detail Popup  ──┐                   │
│              │    │ Name|Category|Pos│                   │
│              │    │ Capacity|Navigate│                   │
│              │    └──────────────────┘                   │
├──────────────┴───────────────────────────────────────────┤
│                              Leaflet | Tianditu          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. 城市切换

1. 点击顶部栏下拉菜单选择城市
2. 地图自动缩放到城市范围
3. 左侧面板自动刷新该城市的设施数据

---

## 4. 选址分析

### 操作步骤

1. 选择 **"选址"** 标签页
2. 调节四个权重滑块（W1~W4）：
   - **W1 人口密度**：倾向于人口密集区域
   - **W2 交通可达性**：倾向于道路发达、靠近铁路站点的区域
   - **W3 竞争回避**：倾向于远离现有同类设施
   - **W4 用地适宜性**：倾向于靠近居住用地
3. 选择目标设施类型（医院 / 诊所 / 药店）
4. 点击 **"运行选址分析"**

> 提示：拖动滑块后系统会在 0.5 秒后自动触发重新计算。

### 结果解读

- **热力图**：绿色→红色渐变，红色 = 高适宜度
- **Top 5 标记**：🥇🥈🥉 金色图标标注前五名网格
- **点击网格行**：地图自动平移到该位置

---

## 5. 路径导航

### 模式一：最近设施

1. 选择 **"导航"** 标签页
2. 导航模式选择 **"最近设施"**
3. 设置起点：点击地图 或 手动输入经纬度
4. 选择目标设施类型
5. 调节 α 值（0~2）：越高越看重设施诊疗能力
6. 点击 **"开始导航"**

### 模式二：指定设施

1. 导航模式选择 **"指定设施"**
2. 选择目标设施（任选一种方式）：
   - **方式 A**：在地图上点击医疗设施标记
   - **方式 B**：在设施属性表中点击 🚘 按钮
   - **方式 C**：在设施详情弹窗中点击"导航到此设施"
3. 设置起点（同上）
4. 点击 **"开始导航"**

### 结果解读

- 路径以**彩色线条**显示在地图上
- **红色** = 最佳路径（综合评分最低）
- **蓝色/绿色** = 候选路径
- 右下角图例显示各路径距离和综合评分
- 点击候选路线卡片可居中查看

---

## 6. 设施属性表

1. 选择 **"设施"** 标签页
2. 功能说明：
   - **搜索框**：输入设施名称实时过滤
   - **分类筛选**：按医院 / 诊所 / 药店 / 其他分类
   - **地图显示勾选框**：独立控制每种设施类型在地图上的显隐
    - **排序**：点击"名称"/"类型"/"能力"表头升降序排列
   - **分页**：30 条/页，底部翻页按钮
3. **点击行**：地图缩放到该设施位置并显示橙色高亮标记
4. **点击 🚘**：自动切换到导航模式并设为目标设施

---

## 7. 容量管理

1. 选择 **"容量"** 标签页
2. **点击地图上的设施**查看详情，左下角弹出详情面板
3. 调整"能力评分"（0~1），点击**"保存"**

> 容量评分越高，路径导航时该设施越容易被优先推荐。

---

## 8. 数据导入

### Web 界面导入

1. 点击顶部 **"导入"** 按钮
2. 输入 GeoJSON/SHP 目录的**服务器端绝对路径**
3. 点击 **"扫描"** 查看检测到的图层
4. 确认显示 ✅ "必要图层齐全"
5. 填写城市名称和标识（英文，如 `beijing`）
6. 点击 **"导入并切换"**

### 配置文件导入

编辑 `config.yaml`，添加城市配置，然后运行：

```bash
python init.py
```

---

## 9. 图层控制

地图右上角按钮 / Basemap selector at top-left:

| 按钮 | 图层 | 说明 |
|---|---|---|
| 🏥 医疗设施 | 设施聚合点 | 默认关，缩放≥16 展开全部 |
| 🏗 用地 | 土地利用面 | 默认开，缩放≥12 可见 |
| 🛣 道路 | 道路网络线 | 默认开，按等级分级显示 |
| 📊 边界 | 行政区划面 | 默认开，自动检测面要素 |
| 🚆 铁路 | 铁路站点聚合 | 默认关，点击弹窗显示站名 |
| 🌍 热力图 | 选址热力图 | 选址分析后自动开 |
| ❌ 清除 | 清除覆盖层 | 清除路线和热力图 |

地图左上角**底图选择器** / Map top-left:

| 按钮 | 说明 |
|---|---|---|
| 天地图 | 国家天地图（需在官网申请 API Key） |
| 无 | 浅灰纯色背景，无需 API Key，仅显示矢量图层 |


---

## 10. 常见问题

**Q: 服务器无法启动？**
- 检查 Python 版本 ≥ 3.10
- 确保已安装依赖：`pip install -r requirements.txt`
- 如端口被占用，修改 `config.yaml` 中 `server.port`
- Windows 用户推荐直接运行 `start.bat`

**Q: 数据导入失败？**
- 确保目录路径存在且可读
- 确保包含 `health`、`landuse`、`roads` 三个必需图层
- CSV 格式需包含经纬度列
- Shapefile 编码默认 UTF-8，如有乱码请转换编码

**Q: 选址分析热力图不显示？**
- 确保已点击"运行选址分析"
- 确保"热力图"图层开关已打开
- 数据量大时计算可能需要 10-30 秒

**Q: 路径导航无结果？**
- 确保起点在数据范围内
- 检查是否有对应类型的设施
- 道路数据需形成连通的网络拓扑

**Q: 能否离线使用？**
- 系统需要互联网连接以加载 Leaflet/Vue CDN
- 默认浅灰色背景无需网络即可显示矢量图层
- 如需完全离线部署，请自行下载 JS 库和本地瓦片服务

**Q: 底图如何切换？**
- 地图左上角有底图选择器：天地图 / 无
- 默认"无"模式为浅灰色背景，无需 API Key
- 选择天地图时需输入 API Key（在天地图官网申请）

---

# English User Guide

## Table of Contents

1. [Overview](#1-overview)
2. [Interface Layout](#2-interface-layout)
3. [City Switching](#3-city-switching)
4. [Suitability Analysis](#4-suitability-analysis)
5. [Route Navigation](#5-route-navigation)
6. [Facility Attribute Table](#6-facility-attribute-table)
7. [Capacity Management](#7-capacity-management)
8. [Data Import](#8-data-import)
9. [Layer Controls](#9-layer-controls)
10. [FAQ](#10-faq)

---

## 1. Overview

This is a WebGIS platform for **spatial site selection analysis** and **route navigation** of medical facilities. It uses a data-agnostic design — switching cities only requires replacing the data configuration.

### Core Concepts

- **Suitability**: Composite suitability score (0~1) for each grid cell. Higher is better.
- **Composite Score**: Route evaluation metric: `Distance - α × Capacity_Score`. Lower is better.
- **Capacity Score**: Facility service capability score (0~10), user-editable, affects route priority.

---

## 2. Interface Layout

```
┌──────────────────────────────────────────────────────────┐
│  Top Bar: Title | City Selector | Import Button          │
├──────────────┬───────────────────────────────────────────┤
│  Left Panel  │         Map Area                          │
│  ┌────────┐  │                                           │
│  │Tabs:   │  │    ┌─ Basemap Selector  ──┐               │
│  │Suit/Nav│  │    │ Tianditu | None      │               │
│  │Fac/Cap │  │    └──────────────────────┘               │
│  └────────┘  │    ┌─ Layer Controls  ──┐                 │
│              │    │ Health|Land|Road   │                 │
│  Param Panel │    │ Rail|Heatmap|Clear │                 │
│  (dynamic)   │    └────────────────────┘                 │
│              │    ┌─ Detail Popup  ──┐                   │
│              │    │ Name|Category|Pos│                   │
│              │    │ Capacity|Navigate│                   │
│              │    └──────────────────┘                   │
├──────────────┴───────────────────────────────────────────┤
│                              Leaflet | Tianditu          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. City Switching

1. Click the dropdown on the top bar to select a city
2. The map auto-fits to the city bounds
3. The left panel refreshes with the city's facility data

---

## 4. Suitability Analysis

### Steps

1. Select the **"选址" (Suitability)** tab
2. Adjust the 4 weight sliders (W1~W4):
   - **W1 Population**: Favors high-population areas
   - **W2 Traffic**: Favors well-connected areas near railway stations
   - **W3 Competition**: Favors distance from existing competitors
   - **W4 Land Use**: Favors proximity to residential land
3. Select target facility type (hospital / clinic / pharmacy)
4. Click **"Run Analysis"**

> Tip: The system auto-triggers recalculation 0.5s after slider adjustment.

### Reading Results

- **Heatmap**: Green→red gradient; red = high suitability
- **Top 5 Markers**: 🥇🥈🥉 gold markers for top 5 grid cells
- **Click a row**: Map pans to that location

---

## 5. Route Navigation

### Mode 1: Nearest Facility

1. Select the **"导航" (Routing)** tab
2. Select **"最近设施" (Nearest Facility)** mode
3. Set start point: click on map or enter lon/lat manually
4. Select target facility type
5. Adjust α (0~2): higher = prioritize capacity
6. Click **"Start Navigation"**

### Mode 2: Specific Facility

1. Select **"指定设施" (Specific Facility)** mode
2. Choose a target facility (any method):
   - **Method A**: Click a facility marker on the map
   - **Method B**: Click the 🚘 button in the attribute table
   - **Method C**: Click "Navigate Here" in the detail popup
3. Set start point (same as above)
4. Click **"Start Navigation"**

### Reading Results

- Routes displayed as **colored lines** on the map
- **Red** = Best route (lowest composite score)
- **Blue/Green** = Alternative routes
- Legend at bottom-right shows distance and composite score
- Click a route card to center the view

---

## 6. Facility Attribute Table

1. Select the **"设施" (Facilities)** tab
2. Features:
   - **Search**: Type a facility name to filter in real-time
   - **Category Filter**: Filter by hospital / clinic / pharmacy / other
   - **Map Visibility Toggles**: Checkboxes to show/hide each facility type on the map
    - **Sort**: Click "Name" / "Type" / "Capacity" column header to sort ascending/descending
   - **Pagination**: 30 items per page with navigation buttons
3. **Click a row**: Map zooms to that facility with an orange highlight marker
4. **Click 🚘**: Auto-switches to routing mode with this facility as the target

---

## 7. Capacity Management

1. Select the **"容量" (Capacity)** tab
2. **Click a facility on the map** — a detail popup appears at bottom-left
3. Adjust the **"Capacity Score"** (0~1), then click **"Save"**

> Higher capacity scores make facilities more likely to be recommended in routing.

---

## 8. Data Import

### Via Web UI

1. Click the **"导入" (Import)** button on the top bar
2. Enter the **server-side absolute path** to the GeoJSON/SHP directory
3. Click **"扫描" (Scan)** to detect layers
4. Confirm ✅ "All required layers found"
5. Fill in the city name and schema ID (e.g., `beijing`)
6. Click **"导入并切换" (Import & Switch)**

### Via Config File

Edit `config.yaml`, add your city configuration, then run:

```bash
python init.py
```

---

## 9. Layer Controls

Buttons at top-right of the map:

| Button | Layer | Description |
|---|---|---|
| 🏥 医疗设施 | Health Facilities | Default off; clustered, all shown at zoom ≥16 |
| 🏗 用地 | Land Use | Default on; visible at zoom ≥12 |
| 🛣 道路 | Roads | Default on; zoom-aware by road class |
| 📊 边界 | Boundary | Default on; auto-detected polygon layer |
| 🚆 铁路 | Railway Stations | Default off; clustered, click for station name |
| 🌍 热力图 | Heatmap | Auto-on after suitability analysis |
| ❌ 清除 | Clear | Remove all overlays |

Basemap selector at map top-left:

| Button | Description |
|---|---|---|
| 天地图 (Tianditu) | National Tianditu (requires API key) |
| 无 (None) | Light-gray background, no API key needed, vector layers only |


---

## 10. FAQ

**Q: Server won't start?**
- Verify Python ≥ 3.10
- Ensure dependencies are installed: `pip install -r requirements.txt`
- If port is occupied, change `server.port` in `config.yaml`
- Windows users: run `start.bat` directly

**Q: Data import fails?**
- Verify the directory path exists and is readable
- Ensure `health`, `landuse`, and `roads` layers are present
- CSV format must include lon/lat columns
- Shapefile encoding defaults to UTF-8; convert if garbled

**Q: Heatmap not showing?**
- Click "Run Analysis" button
- Verify the heatmap layer toggle is ON
- Large datasets may need 10-30s to compute

**Q: No routing results?**
- Ensure the start point is within data bounds
- Check if the target facility type exists
- Road network must form a connected topology

**Q: Can it run offline?**
- The system requires internet for Leaflet/Vue CDN
- Default light-gray background works without any API key
- For fully offline deployment, download JS libraries and local tile service

**Q: How to switch basemaps?**
- Use the basemap selector at the top-left: Tianditu / None
- Default "None" mode shows a light-gray background, no API key needed
- Tianditu requires an API key (apply at tianditu.gov.cn)

---

## 📞 技术支持 / Support

- 提交 Issue 反馈 Bug 或功能建议 / Submit issues for bugs or feature requests
- 技术文档详见 `README.md` / See `README.md` for technical documentation
