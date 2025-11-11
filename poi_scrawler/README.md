# POI Data Collection Pipeline - 完整解决方案

## 📋 问题解决方案总结

### 1. 为什么不需要在采集阶段连数据库？

**原始设计逻辑（正确的分离架构）：**

```
maps_calling.py → 数据采集 + AI增强 → 输出JSON文件
                                          ↓
sync_to_db.py → 读取JSON文件 → 连接数据库 → 同步数据
```

**优点：**
- ✅ **关注点分离**：采集和存储是独立的步骤
- ✅ **容错性强**：数据库问题不影响数据采集
- ✅ **成本可控**：避免因数据库问题浪费付费API额度
- ✅ **灵活性高**：可以先检查数据质量再决定是否同步

### 2. 修复"Database configuration incomplete"错误

**根本原因：**
- `config.py` 中的 `validate_config()` 函数在采集阶段就检查数据库配置
- 但采集阶段不需要数据库配置

**解决方案：**

#### 修改 `config.py`
```python
def validate_config(require_db: bool = False):
    """
    验证配置是否完整
    
    Args:
        require_db: 是否需要验证数据库配置
            - False: 只验证API密钥（数据采集阶段）
            - True: 同时验证数据库配置（数据同步阶段）
    """
    errors = []
    
    # API密钥检查（总是需要）
    if not QWEN_API_KEY:
        errors.append("❌ QWEN_API_KEY not set")
    if not GOOGLE_MAPS_API_KEY:
        errors.append("❌ GOOGLE_MAPS_API_KEY not set")
    
    # 数据库配置检查（可选）
    if require_db:
        missing_db = [k for k, v in DB_CONFIG.items() if not v]
        if missing_db:
            errors.append(f"❌ DB config incomplete: {missing_db}")
    
    if errors:
        for error in errors:
            print(error)
        return False
    
    print("✅ Configuration validated")
    if not require_db and not all(DB_CONFIG.values()):
        print("ℹ️  Database not required for this step")
    
    return True
```

#### 修改 `maps_calling.py`
```python
def main():
    # 数据采集阶段不需要数据库配置
    if not validate_config(require_db=False):
        return
    # ... 其余代码
```

#### 修改 `sync_to_db.py`
```python
def main():
    # 数据同步阶段必须验证数据库配置
    if not validate_config(require_db=True):
        return
    # ... 其余代码
```

### 3. 修复"File not found: paris_comprehensive_database.json"错误

**根本原因：**
- GitHub Actions 的工作目录设置导致路径混乱
- JSON文件在 `src/` 目录生成，但 `sync_to_db.py` 在错误的目录运行

**解决方案：**

#### 方法A：确保在正确目录运行（推荐）
```yaml
- name: Sync Data to Cloud SQL
  env:
    DB_HOST: "127.0.0.1"
    DB_PORT: "5432"
    DB_USER: ${{ secrets.DB_USER }}
    DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
    DB_NAME: ${{ secrets.DB_NAME }}
  run: |
    cd src
    ls -la *.json  # 调试：显示JSON文件
    python sync_to_db.py
```

#### 方法B：在 `sync_to_db.py` 中增强文件查找
```python
def sync_to_database(json_filepath: str):
    # 检查文件是否存在
    if not os.path.exists(json_filepath):
        print(f"❌ File not found: {json_filepath}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Available JSON files:")
        for f in os.listdir('.'):
            if f.endswith('.json'):
                print(f"      - {f}")
        return
    # ... 其余代码
```

## 🎯 智能采集策略：150 + 去重 + 50补充

### 策略说明

**目标：** 收集200个高质量、无重复的POI

**实施步骤：**

1. **第一阶段：初始采集（~150个）**
   - 按POI类型（餐厅/景点/酒店）平均分配
   - 每个关键词采集10个POI
   - 实时去重（地理位置 + 名称相似度）

2. **第二阶段：验证和统计**
   - 检查每个类型的POI数量
   - 识别缺口

3. **第三阶段：补充采集（~50个）**
   - 针对不足的POI类型
   - 增加每个关键词的采集数量
   - 继续实时去重

4. **第四阶段：AI增强**
   - 批量调用Qwen API
   - 添加标签、分类、价格等信息

### 去重算法

```python
def is_duplicate(poi: Dict, existing_pois: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    检查POI是否重复
    
    检查维度：
    1. Place ID是否相同（Google的唯一标识）
    2. 地理位置距离 < 50米 且 名称相似度 > 0.85
    """
    # 检查Place ID
    if poi['google_place_id'] == existing['google_place_id']:
        return True, "Place ID重复"
    
    # 检查地理位置 + 名称
    distance = haversine_distance(poi_lat, poi_lng, existing_lat, existing_lng)
    if distance < 50:  # 50米阈值
        similarity = calculate_name_similarity(poi_name, existing_name)
        if similarity > 0.85:  # 85%相似度阈值
            return True, f"位置重复({distance}m) + 名称相似({similarity})"
    
    return False, None
```

### 使用方法

#### 选项1：使用智能采集脚本（推荐）
```bash
cd poi_scrawler/src
python maps_calling_smart.py
```

#### 选项2：在GitHub Actions中自动选择
```yaml
- name: Run POI Data Collection
  run: |
    cd src
    if [ -f "maps_calling_smart.py" ]; then
      echo "Using smart collection strategy..."
      python maps_calling_smart.py
    else
      python maps_calling.py
    fi
```

## 📁 文件结构

```
poi_scrawler/
├── src/
│   ├── config.py                    # 配置管理（已修复）
│   ├── maps_calling.py              # 标准采集脚本
│   ├── maps_calling_smart.py        # 智能采集脚本（新增）
│   ├── sync_to_db.py                # 数据库同步（已修复）
│   └── paris_comprehensive_database.json  # 输出文件
├── requirements.txt
└── .github/
    └── workflows/
        └── poi_data_collection.yml  # GitHub Actions工作流（已修复）
```

## 🚀 部署步骤

### 1. 替换修改后的文件

```bash
# 替换 config.py
cp /home/claude/config.py poi_scrawler/src/config.py

# 替换 sync_to_db.py
cp /home/claude/sync_to_db.py poi_scrawler/src/sync_to_db.py

# 添加智能采集脚本
cp /home/claude/maps_calling_smart.py poi_scrawler/src/maps_calling_smart.py

# 替换 GitHub Actions workflow
cp /home/claude/poi_data_collection.yml .github/workflows/poi_data_collection.yml
```

### 2. 验证GitHub Secrets

确保以下secrets已配置：

```
✅ GOOGLE_MAPS_API_KEY
✅ QWEN_API_KEY
✅ GCP_SA_KEY
✅ GCSQL_INSTANCE_NAME
✅ DB_USER
✅ DB_PASSWORD
✅ DB_NAME
```

### 3. 测试运行

#### 本地测试（数据采集）
```bash
cd poi_scrawler/src

# 设置环境变量
export GOOGLE_MAPS_API_KEY="your_key"
export QWEN_API_KEY="your_key"

# 运行智能采集
python maps_calling_smart.py
```

#### 本地测试（数据库同步）
```bash
# 设置数据库环境变量
export DB_HOST="127.0.0.1"
export DB_PORT="5432"
export DB_USER="your_user"
export DB_PASSWORD="your_password"
export DB_NAME="your_db"

# 运行同步
python sync_to_db.py
```

#### GitHub Actions测试
```bash
# 推送到GitHub
git add .
git commit -m "Fix: POI collection pipeline issues"
git push

# 手动触发workflow
# 在GitHub仓库页面：Actions → POI Data Collection Pipeline → Run workflow
```

## 📊 预期结果

### 采集阶段输出
```
════════════════════════════════════════════════════════════════════
✅ SUCCESS!
════════════════════════════════════════════════════════════════════
📁 Output file: paris_comprehensive_database.json
📊 Final Statistics:
   - Total POIs: 200
   - Restaurants: 67
   - Attractions: 66
   - Hotels: 67
   - Target Achievement: 200/200 (100.0%)
════════════════════════════════════════════════════════════════════
```

### 同步阶段输出
```
════════════════════════════════════════════════════════════════════
📤 Database Synchronization - Starting
════════════════════════════════════════════════════════════════════

✅ Loaded 200 POIs from paris_comprehensive_database.json

📊 POI Distribution:
   Restaurant: 67
   Attraction: 66
   Hotel: 67

✅ Database connection established

🔄 Syncing 67 restaurants...
✅ Synced 67 restaurant records

🔄 Syncing 66 attractions...
✅ Synced 66 attraction records

🔄 Syncing 67 hotels...
✅ Synced 67 hotel records

════════════════════════════════════════════════════════════════════
✅ SUCCESS!
════════════════════════════════════════════════════════════════════
📊 Total records synced: 200
════════════════════════════════════════════════════════════════════
```

## 🔧 故障排除

### 问题1：仍然报"Database configuration incomplete"
```bash
# 检查config.py是否正确更新
grep "require_db" poi_scrawler/src/config.py

# 确保maps_calling.py调用时使用require_db=False
grep "validate_config" poi_scrawler/src/maps_calling.py
```

### 问题2：JSON文件找不到
```bash
# 检查文件是否生成
ls -la poi_scrawler/src/*_comprehensive_database.json

# 检查工作目录
pwd
```

### 问题3：数据库连接失败
```bash
# 检查Cloud SQL Proxy是否运行
ps aux | grep cloud-sql-proxy

# 测试本地连接
nc -zv 127.0.0.1 5432
```

## 📈 性能优化建议

1. **API成本控制**
   - Google Maps API: 每个POI需要2次调用（搜索+详情）
   - Qwen API: 批量处理，每批20个POI
   - 预计成本：~$5-10 per 200 POIs

2. **执行时间**
   - 数据采集：~30-45分钟（包含API等待时间）
   - AI增强：~5-10分钟
   - 数据库同步：~1-2分钟
   - 总计：~40-60分钟

3. **并发优化**（可选）
   - 使用异步请求提高采集速度
   - 注意API速率限制

## 📝 下一步计划

- [ ] 部署修复后的代码
- [ ] 测试GitHub Actions workflow
- [ ] 监控第一次完整运行
- [ ] 根据结果调整参数（如去重阈值）
- [ ] 考虑添加数据质量报告