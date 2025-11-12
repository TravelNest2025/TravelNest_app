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
    生成AI标注的Prompt
    
    Args:
        poi_type: POI类型 ('restaurant', 'attraction', 'hotel')
        poi_list: POI列表，每个POI包含name和google_types
    
    Returns:
        完整的AI prompt字符串
    """
    
    # 简化POI信息
    simplified_pois = [
        {
            "name": poi.get("name"),
            "types": poi.get("google_types", []),
            "address": poi.get("address", "")[:50]  # 只取地址前50个字符
        }
        for poi in poi_list
    ]
    
    # 根据POI类型定制Prompt
    if poi_type == "restaurant":
        specific_instructions = """
For RESTAURANTS, provide:
1. **ai_tags**: Select 3-5 relevant tags from the available tags list. Focus on:
   - Food style (local_cuisine, michelin, fine_dining, cafe)
   - Dining scene (romantic, scenic_view)
   - Atmosphere tags if applicable
   
2. **categories**: Select 1-2 categories (usually 'food', optionally add 'romantic', 'leisure', etc.)

3. **name_cn**: Translate the restaurant name to Chinese (keep original if it's a proper name)

4. **avg_price_per_person**: Estimate average price per person in EUR (e.g., 45.00)

5. **price_range_label**: Choose one from ['low', 'mid', 'high', 'luxury'] based on Paris standards:
   - low: €50-90
   - mid: €90-150
   - high: €150-250
   - luxury: €250+

6. **is_michelin**: Boolean, true if it's a Michelin-starred restaurant

7. **michelin_stars**: Integer (1-3) if is_michelin is true, otherwise null
"""
    
    elif poi_type == "attraction":
        specific_instructions = """
For ATTRACTIONS, provide:
1. **ai_tags**: Select 3-5 relevant tags from the available tags list. Focus on:
   - Type (museum, historical_site, art_gallery, etc.)
   - Experience (instagram_worthy, family_activity)
   - Nature tags if applicable
   
2. **categories**: Select 1-2 categories (culture, nature, urban, leisure, etc.)

3. **name_cn**: Translate the attraction name to Chinese

4. **ticket_price**: Estimate ticket price in EUR (e.g., 15.00), use 0.00 for free attractions

5. **price_range_label**: Choose one from ['free', 'low', 'mid', 'high']:
   - free: €0
   - low: €0-15
   - mid: €15-30
   - high: €30+

6. **is_free_entry**: Boolean, true if the attraction is free

7. **visit_duration**: Estimated visit duration in minutes (e.g., 120)

8. **description**: Brief description in English (50-100 words)
"""
    
    else:  # hotel
        specific_instructions = """
For HOTELS, provide:
1. **ai_tags**: Select 3-5 relevant tags from the available tags list. Focus on:
   - Style (romantic, resort, spa_wellness)
   - Target audience (kids_friendly, pet_friendly)
   - Location (urban_landmark if in city center)
   
2. **categories**: Select 1-2 categories (usually 'romantic', 'family', 'leisure', 'urban')

3. **name_cn**: Translate the hotel name to Chinese (keep brand names in original language)

4. **price_per_night**: Estimate price per night in EUR (e.g., 180.00)

5. **price_range_label**: Choose one from ['low', 'mid', 'high', 'luxury'] based on Paris standards:
   - low: €50-100
   - mid: €100-200
   - high: €200-350
   - luxury: €350+

6. **star_rating**: Hotel star rating (1-5), or null if not a traditional hotel
"""
    
    prompt = f"""You are a professional travel data analyst specializing in {TARGET_CITY}. Your task is to analyze a list of POIs and provide structured data.

**AVAILABLE TAGS** (select from these 26 tags):
{', '.join(AVAILABLE_TAGS)}

**AVAILABLE CATEGORIES** (select from these 8 categories):
{', '.join(AVAILABLE_CATEGORIES)}

**POI TYPE**: {poi_type}

**INSTRUCTIONS**:
{specific_instructions}

**POI LIST TO ANALYZE**:
{json.dumps(simplified_pois, indent=2, ensure_ascii=False)}

**OUTPUT FORMAT**:
Your response MUST be a valid JSON object with a single key "enriched_data".
The value should be an array of objects, one for each POI in the same order as the input.

Each object MUST contain:
- "name": string (original name for matching)
- "name_cn": string (Chinese translation)
- "ai_tags": array of strings (3-5 tags from the available tags)
- "categories": array of strings (1-2 categories from the available categories)
- Additional fields based on POI type as specified above

**CRITICAL RULES**:
1. All tag names must EXACTLY match the available tags list (case-sensitive)
2. All category names must EXACTLY match the available categories list (case-sensitive)
3. Return EXACTLY the same number of objects as the input POI list
4. Use the "name" field to match input and output POIs
5. DO NOT include any text outside the JSON structure
6. DO NOT use markdown code blocks (no ```json```)

**EXAMPLE OUTPUT STRUCTURE** (for reference only):
{{
  "enriched_data": [
    {{
      "name": "Le Jules Verne",
      "name_cn": "儒勒·凡尔纳餐厅",
      "ai_tags": ["fine_dining", "scenic_view", "romantic", "michelin"],
      "categories": ["food", "romantic"],
      "avg_price_per_person": 250.00,
      "price_range_label": "luxury",
      "is_michelin": true,
      "michelin_stars": 1
    }}
  ]
}}

Now analyze the POI list and return the enriched data in the exact format specified above.
"""
    
    return prompt


# ==============================================================================
# 验证函数
# ==============================================================================

def validate_config(require_db: bool = False):
    """
    验证配置是否完整
    
    Args:
        require_db: 是否需要验证数据库配置（默认False）
            - False: 只验证API密钥（用于数据采集阶段）
            - True: 同时验证数据库配置（用于数据同步阶段）
    
    Returns:
        bool: 配置是否有效
    """
    errors = []
    
    # API密钥检查（总是需要）
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