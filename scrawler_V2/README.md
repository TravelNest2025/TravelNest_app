# TravelNest POI Data Collector

使用 Google Places API 采集 POI 数据的自动化工具。

## 功能特性

- ✅ 支持采集餐厅、景点、酒店数据
- ✅ 自动分类映射 (Google types → 自定义 categories)
- ✅ 批量插入和更新
- ✅ GitHub Actions 自动化
- ✅ 完整的日志记录

## 快速开始

### 1. 配置 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets:

**数据库配置:**
- `DB_HOST`: 数据库主机地址
- `DB_PORT`: 数据库端口 (默认 5432)
- `DB_NAME`: 数据库名称
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码

**API 配置:**
- `GOOGLE_PLACES_API_KEY`: Google Places API 密钥

### 2. 本地开发
```bash
# 克隆仓库
git clone <your-repo-url>
cd travelnest-poi-collector

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=poi-database
export DB_USER=postgres
export DB_PASSWORD=your_password
export GOOGLE_PLACES_API_KEY=your_api_key

# 运行采集
python -m src.collector --city-id paris --poi-type restaurants --limit 100
```

### 3. 使用 GitHub Actions

**手动触发:**
1. 进入 GitHub 仓库的 Actions 页面
2. 选择 "POI Data Collection" workflow
3. 点击 "Run workflow"
4. 填写参数:
   - `city_id`: 城市 ID (如: paris)
   - `poi_type`: POI 类型 (restaurants/attractions/hotels/all)
   - `limit`: 最大采集数量 (0 = 无限制)

## 项目结构
```
.
├── .github/
│   └── workflows/
│       └── POI_Data_cralwler(Single_City).yml      # GitHub Actions 配置
├── src/
│   ├── __init__.py
│   ├── config.py                 # 配置管理
│   ├── crawler.py                # 主采集逻辑
│   ├── models.py                 # Google API 客户端
│   ├── type_mapping.py           # 分类映射
│   └── writer.py                 #数据库写入 
├── logs/                         # 日志目录
├── requirements.txt              # Python 依赖
└── README.md
```

## 数据流程
```
1. 从数据库读取城市配置
2. 使用 Google Places API 搜索 POIs
   - 按关键词搜索
   - 按类型搜索
3. 获取每个 POI 的详细信息
4. 映射 Google types → 自定义 categories
5. 批量插入/更新数据库
6. 记录采集日志
```

## API 配额管理

- Google Places API 免费额度: 每月 $200
- 每次 API 调用:
  - Nearby Search: $0.032 / 次
  - Place Details: $0.017 / 次
- 建议: 设置 `limit` 参数控制采集数量

## 监控和日志

- 日志文件保存在 `logs/` 目录
- GitHub Actions 会自动上传日志作为 artifacts
- 数据库 `collection_logs` 表记录每次采集的统计信息

## 故障排查

**问题: API 调用失败**
- 检查 `GOOGLE_PLACES_API_KEY` 是否正确
- 确认 API 已启用且有额度

**问题: 数据库连接失败**
- 检查数据库凭据是否正确
- 确认数据库允许远程连接 (检查防火墙)

**问题: 没有找到 POIs**
- 检查城市坐标是否正确
- 尝试增大搜索半径 (`search_radius`)
```

---

## 9️⃣ GitHub Secrets 配置指南

在 GitHub 仓库中配置 Secrets:

1. **进入仓库设置**
```
   仓库 → Settings → Secrets and variables → Actions → New repository secret
```

2. **添加以下 Secrets:**
```
   名称: DB_HOST
   值: your-database-host.com
   
   名称: DB_PORT
   值: 5432
   
   名称: DB_NAME
   值: poi-database
   
   名称: DB_USER
   值: postgres
   
   名称: DB_PASSWORD
   值: your-secure-password
   
   名称: GOOGLE_PLACES_API_KEY

   值: AIzaSy...your-google-api-key
