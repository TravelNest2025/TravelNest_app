"""
配置管理模块
集中管理所有配置信息，包括API密钥、搜索关键词、城市信息等
"""
import os
import json
from typing import Dict, List

# ==============================================================================
# API配置
# ==============================================================================

# 阿里云Qwen API配置 (通过OpenAI SDK调用)
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")  # 阿里云API Key
QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"  # 阿里云兼容端点
QWEN_MODEL = "qwen3-max-preview"  # 使用qwen-max模型

# Google Maps API配置
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# 数据库配置
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD")
}

# ==============================================================================
# 数据采集配置
# ==============================================================================

# 目标城市
TARGET_CITY = "Paris"
CITY_ID = "paris"
DB_SCHEMA = "poi_data"

# AI处理批次大小
AI_BATCH_SIZE = 20  # 每批处理20个POI，平衡速度和成本

# 每个关键词搜索的POI数量限制
POIS_PER_KEYWORD = 20

# ==============================================================================
# 搜索关键词配置
# ==============================================================================

SEARCH_KEYWORDS = {
    "restaurant": [
        "Michelin restaurants",
        "French bistros",
        "cafes and bakeries",
        "fine dining restaurants",
        "local cuisine restaurants",
        "romantic restaurants"
    ],
    "attraction": [
        "art museums",
        "historical landmarks",
        "parks and gardens",
        "iconic monuments",
        "art galleries",
        "cultural sites"
    ],
    "hotel": [
        "boutique hotels",
        "luxury hotels",
        "budget hotels",
        "hotels with spa",
        "family hotels",
        "romantic hotels"
    ]
}

# ==============================================================================
# AI标注配置
# ==============================================================================

# 26个标签（从tag_definitions表）
AVAILABLE_TAGS = [
    # CULTURE (文化艺术)
    'historical_site', 'museum', 'art_gallery', 'live_performance',
    # NATURE (自然风光)
    'beach', 'mountain', 'national_park',
    # FOOD (美食体验)
    'local_cuisine', 'michelin', 'scenic_view', 'fine_dining', 'cafe',
    # LEISURE (休闲娱乐)
    'shopping', 'nightlife', 'theme_park', 'spa_wellness', 'instagram_worthy',
    # ADVENTURE (探险活动)
    'outdoor_sports', 'wildlife',
    # ROMANTIC (浪漫度假)
    'romantic', 'resort',
    # FAMILY (亲子家庭)
    'kids_friendly', 'family_activity', 'pet_friendly',
    # URBAN (都市体验)
    'urban_landmark', 'modern_architecture'
]

# 8个分类（从category_definitions表）
AVAILABLE_CATEGORIES = [
    'culture',      # 文化艺术
    'nature',       # 自然风光
    'food',         # 美食体验
    'leisure',      # 休闲娱乐
    'adventure',    # 探险活动
    'romantic',     # 浪漫度假
    'family',       # 亲子家庭
    'urban'         # 都市体验
]

# ==============================================================================
# AI Prompt模板
# ==============================================================================

def get_ai_prompt(poi_type: str, poi_list: List[Dict]) -> str:
    """
    生成AI标注的Prompt（增强版）
    
    Args:
        poi_type: POI类型
        poi_list: POI列表，包含详细信息
    
    Returns:
        完整的AI prompt字符串
    """
    
    # 简化但保留关键信息
    simplified_pois = []
    for poi in poi_list:
        poi_info = {
            "name": poi.get("name"),
            "rating": poi.get("rating"),
            "review_count": poi.get("review_count", 0),
            "types": poi.get("types", [])
        }
        
        # 添加价格信息（如果有）
        if poi.get("price_level") is not None:
            price_labels = {0: "Free", 1: "€", 2: "€€", 3: "€€€", 4: "€€€€"}
            poi_info["price_level"] = price_labels.get(poi.get("price_level"), "Unknown")
        
        # 添加 Google 介绍（如果有）
        if poi.get("editorial_summary"):
            poi_info["google_description"] = poi.get("editorial_summary")[:150]
        
        # 添加评论关键词（如果有）
        if poi.get("review_keywords"):
            poi_info["review_highlights"] = poi.get("review_keywords")
        
        simplified_pois.append(poi_info)
    
    # 根据POI类型定制Prompt
    if poi_type == "restaurant":
        specific_instructions = """
For RESTAURANTS, provide:
1. **ai_tags**: Select 3-5 relevant tags. Consider:
   - Food style from types and description
   - Price level indicator
   - Review highlights (romantic, family_friendly, etc.)
   
2. **categories**: Select 1-2 categories (usually 'food', optionally 'romantic', 'leisure')

3. **name_cn**: Chinese translation

4. **avg_price_per_person**: Estimate based on price_level:
   - €: 15-30
   - €€: 30-60
   - €€€: 60-120
   - €€€€: 120+

5. **price_range_label**: ['low', 'mid', 'high', 'luxury']

6. **is_michelin**: Check google_description or review_highlights for "michelin"

7. **michelin_stars**: 1-3 if is_michelin is true
"""
    
    elif poi_type == "attraction":
        specific_instructions = """
For ATTRACTIONS, provide:
1. **ai_tags**: Select 3-5 tags based on types and description

2. **categories**: Select 1-2 categories

3. **name_cn**: Chinese translation

4. **ticket_price**: Estimate based on price_level or google_description

5. **price_range_label**: ['free', 'low', 'mid', 'high']

6. **is_free_entry**: Boolean

7. **visit_duration**: Estimate in minutes (60-240)

8. **description**: Use google_description if available, or create brief summary
"""
    
    else:  # hotel
        specific_instructions = """
For HOTELS, provide:
1. **ai_tags**: Select 3-5 tags. Consider:
   - Review highlights (romantic, spa_wellness, kids_friendly)
   - Location (urban_landmark if in city center)

2. **categories**: ['romantic', 'family', 'leisure', 'urban']

3. **name_cn**: Chinese translation

4. **price_per_night**: Estimate based on price_level:
   - €: 50-100
   - €€: 100-200
   - €€€: 200-350
   - €€€€: 350+

5. **price_range_label**: ['low', 'mid', 'high', 'luxury']

6. **star_rating**: 1-5
"""
    
    prompt = f"""You are a professional travel data analyst for {TARGET_CITY}.

**AVAILABLE TAGS**: {', '.join(AVAILABLE_TAGS)}

**AVAILABLE CATEGORIES**: {', '.join(AVAILABLE_CATEGORIES)}

**POI TYPE**: {poi_type}

**INSTRUCTIONS**:
{specific_instructions}

**POI DATA** (with Google descriptions and review insights):
{json.dumps(simplified_pois, indent=2, ensure_ascii=False)}

**OUTPUT FORMAT**:
{{
  "enriched_data": [
    {{
      "name": "...",
      "name_cn": "...",
      "ai_tags": ["tag1", "tag2", ...],
      "categories": ["cat1", ...],
      ... (other fields)
    }}
  ]
}}

**CRITICAL**:
- Use exact tag/category names from available lists
- Use google_description and review_highlights to make informed decisions
- Match "name" field for each POI
- Return pure JSON, no markdown
"""
    
    return prompt


# ==============================================================================
# 验证函数
# ==============================================================================

def validate_config(require_db: bool = False, require_apis: bool = True):
    """
    验证配置是否完整
    
    Args:
        require_db: 是否需要验证数据库配置（默认False）
            - False: 不验证数据库配置
            - True: 验证数据库配置（用于数据同步阶段）
        require_apis: 是否需要验证API密钥（默认True）
            - True: 验证API密钥（用于数据采集阶段）
            - False: 不验证API密钥（用于仅数据库同步）
    
    Returns:
        bool: 配置是否有效
    """
    errors = []
    
    # API密钥检查（可选）
    if require_apis:
        if not QWEN_API_KEY:
            errors.append("❌ QWEN_API_KEY environment variable not set")
        
        if not GOOGLE_MAPS_API_KEY:
            errors.append("❌ GOOGLE_MAPS_API_KEY environment variable not set")
    
    # 数据库配置检查（可选）
    if require_db:
        missing_db_configs = [k for k, v in DB_CONFIG.items() if not v]
        if missing_db_configs:
            errors.append(f"❌ Database configuration incomplete. Missing: {', '.join(missing_db_configs)}")
    
    # 打印错误信息
    if errors:
        print("\n" + "="*60)
        print("⚠️  Configuration Validation Failed")
        print("="*60)
        for error in errors:
            print(error)
        print("="*60 + "\n")
        return False
    
    # 配置验证成功
    print("✅ Configuration validated successfully")
    
    # 如果不需要数据库配置，但数据库配置缺失，给出提示
    if not require_db and not all(DB_CONFIG.values()):
        print("ℹ️  Database configuration not required for this step")
    
    return True