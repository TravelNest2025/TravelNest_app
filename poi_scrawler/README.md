# 🌍 POI Data Collection Pipeline

一个完整的POI（Point of Interest）数据采集系统，从Google Maps获取数据，使用阿里云Qwen AI进行智能标注，并自动同步到Google Cloud SQL数据库。

## 📋 系统架构

```
GitHub Actions (每周自动运行)
    ↓
Google Maps API (获取POI基础数据)
    ↓
Alibaba Qwen AI (智能标注和增强)
    ↓
JSON文件 (临时存储)
    ↓
Cloud SQL Proxy (安全连接)
    ↓
Google Cloud SQL (PostgreSQL数据库)
```

## 🚀 快速开始

### 前置要求

1. **Google Cloud账号**
   - 启用Cloud SQL API
   - 创建PostgreSQL实例
   - 创建服务账号并授予`Cloud SQL Client`角色

2. **API密钥**
   - Google Maps API Key
   - 阿里云Qwen API Key (DashScope)

3. **GitHub仓库**
   - 用于托管代码和运行GitHub Actions

### 步骤1：设置数据库

连接到您的Cloud SQL实例，执行Schema脚本创建所有必要的表：

```bash
psql -h YOUR_DB_HOST -U YOUR_DB_USER -d YOUR_DB_NAME -f sprint1_schema.sql
```

### 步骤2：配置GitHub Secrets

在GitHub仓库的`Settings > Secrets and variables > Actions`中添加以下secrets：

| Secret名称 | 说明 | 示例 |
|-----------|------|------|
| `GOOGLE_MAPS_API_KEY` | Google Maps API密钥 | `AIzaSy...` |
| `QWEN_API_KEY` | 阿里云Qwen API密钥 | `sk-...` |
| `GCP_SA_KEY` | Google Cloud服务账号JSON密钥 | `{"type": "service_account",...}` |
| `GCSQL_INSTANCE_NAME` | Cloud SQL实例连接名 | `project:region:instance` |
| `DB_USER` | 数据库用户名 | `postgres` |
| `DB_PASSWORD` | 数据库密码 | `your_password` |
| `DB_NAME` | 数据库名称 | `poi_database` |

### 步骤3：部署代码

```bash
# 克隆仓库
git clone https://github.com/your-username/poi-data-pipeline.git
cd poi-data-pipeline

# 推送到GitHub（会自动触发workflow）
git add .
git commit -m "Initial deployment"
git push origin main
```

### 步骤4：手动触发采集

1. 进入GitHub仓库的`Actions`标签
2. 选择`POI Data Collection Pipeline`工作流
3. 点击`Run workflow`按钮
4. 选择分支并点击`Run workflow`

## 📂 项目结构

```
poi-data-pipeline/
├── .github/
│   └── workflows/
│       └── collect_data.yml      # GitHub Actions工作流
├── src/
│   ├── config.py                 # 配置管理
│   ├── maps_calling.py           # 数据获取和AI增强
│   └── sync_to_db.py             # 数据库同步
├── requirements.txt               # Python依赖
├── .gitignore                    # Git忽略文件
└── README.md                     # 项目文档
```

## ⚙️ 配置说明

### 修改目标城市

编辑`src/config.py`：

```python
TARGET_CITY = "Paris"  # 改为您想要的城市
CITY_ID = "paris"      # 改为对应的city_id
```

### 调整搜索关键词

编辑`src/config.py`中的`SEARCH_KEYWORDS`：

```python
SEARCH_KEYWORDS = {
    "restaurant": [
        "Michelin restaurants",
        "French bistros",
        # 添加更多关键词...
    ],
    # ...
}
```

### 调整AI批处理大小

```python
AI_BATCH_SIZE = 20  # 增大以提高速度，减小以降低成本
```

## 🔧 本地开发与测试

### 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 设置环境变量

创建`.env`文件（不要提交到Git）：

```bash
export GOOGLE_MAPS_API_KEY="your_key"
export QWEN_API_KEY="your_key"
export DB_HOST="127.0.0.1"
export DB_PORT="5432"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
export DB_NAME="poi_database"
```

### 本地运行

```bash
# 启动Cloud SQL Proxy（如果使用Cloud SQL）
./cloud-sql-proxy your-project:region:instance &

# 运行数据采集
cd src
python maps_calling.py

# 运行数据同步
python sync_to_db.py
```

## 📊 数据流程说明

### 1. 数据采集 (maps_calling.py)

```
搜索关键词 → Google Places API
    ↓
获取Place ID列表
    ↓
批量获取详细信息
    ↓
筛选有效POI（排除永久关闭）
    ↓
按类型分组（restaurant/attraction/hotel）
```

### 2. AI增强 (maps_calling.py)

```
POI基础数据（名称、地址、类型）
    ↓
生成智能Prompt
    ↓
调用阿里云Qwen API
    ↓
解析JSON响应
    ↓
合并AI数据到POI
    ↓
输出：
  - ai_tags: ['michelin', 'romantic', ...]
  - categories: ['food', 'romantic']
  - name_cn: 中文名称
  - avg_price_per_person: 估算价格
  - 其他增强字段...
```

### 3. 数据同步 (sync_to_db.py)

```
读取JSON文件
    ↓
按POI类型分组
    ↓
准备数据（处理PostGIS地理坐标）
    ↓
构建Upsert SQL
    ↓
批量执行（execute_values）
    ↓
提交事务
```

## 🎯 核心特性

### ✅ 智能数据采集

- 使用多个关键词全面搜索
- 自动去重（基于Place ID）
- 获取完整的POI详细信息（评分、照片、营业时间等）
- 过滤永久关闭的POI

### 🤖 AI智能标注

- 使用阿里云Qwen-Max模型
- 26个精准标签（文化、美食、娱乐等）
- 8个主分类
- 中文名称翻译
- 价格预估和档位分类
- 米其林星级识别
- 景点游玩时长估算

### 🔄 数据库同步

- Upsert机制（INSERT ... ON CONFLICT）
- PostGIS地理坐标处理
- 批量操作（高性能）
- 事务保证（原子性）
- 自动更新时间戳

### 🛡️ 生产级质量

- 错误处理和重试机制
- 详细日志输出
- API速率限制控制
- 安全的认证方式（Cloud SQL Auth Proxy）
- 自动化调度（GitHub Actions）

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| POI处理速度 | ~20个POI/分钟（含AI标注） |
| Google Maps API调用 | ~150次/运行（巴黎） |
| Qwen API Token消耗 | ~500 tokens/POI |
| 数据库写入速度 | ~1000条/秒（批量操作） |
| 总运行时间 | ~15-20分钟（完整流程） |

## 💰 成本估算

### Google Maps API

- 免费额度：$200/月
- Places API: $17/1000次请求
- 估算成本：~$2.50/周运行

### 阿里云Qwen API

- Qwen-Max: ¥0.04/1000 tokens
- 估算成本：~¥3/周运行（约$0.42）

### Google Cloud SQL

- db-f1-micro: ~$9/月
- 10GB存储: ~$1.7/月
- 估算成本：~$10.7/月

**总成本：~$20-30/月**（包含所有服务）

## 🔍 故障排查

### 问题1：GitHub Actions运行失败

**检查清单：**
- [ ] 所有Secrets是否正确配置？
- [ ] Cloud SQL实例是否运行中？
- [ ] 服务账号是否有正确权限？

### 问题2：AI标注结果不准确

**解决方案：**
- 调整`config.py`中的Prompt模板
- 增加示例POI
- 调整temperature参数（当前0.7）

### 问题3：数据库连接超时

**解决方案：**
```yaml
# 增加代理启动等待时间
sleep 5  # 改为 sleep 10
```

### 问题4：API配额超限

**解决方案：**
- 减少`POIS_PER_KEYWORD`
- 减少`SEARCH_KEYWORDS`数量
- 增加API调用间隔`time.sleep()`

## 📝 开发路线图

- [x] 基础数据采集
- [x] AI智能标注
- [x] 数据库同步
- [x] GitHub Actions自动化
- [ ] 增量更新（仅更新变化的POI）
- [ ] 多城市支持
- [ ] 实时营业状态更新
- [ ] Web管理界面
- [ ] 数据质量监控面板

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 👥 作者

您的名字

---

**⭐ 如果这个项目对您有帮助，请给个Star！**