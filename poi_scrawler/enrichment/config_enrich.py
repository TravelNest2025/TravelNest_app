"""
标签增强配置文件
独立于主采集流程的配置
"""
import os
from typing import Dict, List

# ==============================================================================
# API 配置
# ==============================================================================

# 阿里云 Qwen API
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-max"

# Google Maps API
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# 数据库配置
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD")
}

DB_SCHEMA = "poi_data"

# ==============================================================================
# 高价值 POI 筛选标准
# ==============================================================================

HIGH_VALUE_CRITERIA = {
    # 标准1：评论数超过 700
    'high_review_threshold': 700,
    
    # 标准2：评分 > 4.3 且评论数 > 300
    'quality_rating_threshold': 4.3,
    'quality_review_threshold': 300,
    
    # 每批处理数量
    'batch_size': 20,
    
    # 每个表最多处理多少个 POI
    'max_pois_per_table': 50
}

# ==============================================================================
# 映射规则：Google Types → Categories
# ==============================================================================

TYPE_TO_CATEGORIES = {
    # FOOD 美食体验
    'restaurant': ['food'],
    'cafe': ['food', 'leisure'],
    'bar': ['food', 'leisure'],
    'bakery': ['food'],
    'meal_takeaway': ['food'],
    'meal_delivery': ['food'],
    'food': ['food'],
    
    # CULTURE 文化艺术
    'museum': ['culture'],
    'art_gallery': ['culture'],
    'library': ['culture'],
    'church': ['culture'],
    'synagogue': ['culture'],
    'mosque': ['culture'],
    'place_of_worship': ['culture'],
    'tourist_attraction': ['culture'],
    'historical_landmark': ['culture'],
    'landmark': ['culture'],
    
    # NATURE 自然风光
    'park': ['nature'],
    'natural_feature': ['nature'],
    'campground': ['nature', 'adventure'],
    
    # LEISURE 休闲娱乐
    'shopping_mall': ['leisure'],
    'store': ['leisure'],
    'night_club': ['leisure'],
    'amusement_park': ['leisure', 'family'],
    'spa': ['leisure', 'romantic'],
    'movie_theater': ['leisure'],
    
    # ADVENTURE 探险活动
    'zoo': ['adventure', 'family'],
    'aquarium': ['adventure', 'family'],
    
    # ROMANTIC 浪漫度假
    'lodging': ['romantic'],
    
    # FAMILY 亲子家庭
    'playground': ['family'],
    
    # URBAN 都市体验
    'point_of_interest': ['urban'],
    'establishment': ['urban'],
    'city_hall': ['urban', 'culture'],
    'train_station': ['urban'],
    'subway_station': ['urban'],
}

# ==============================================================================
# 映射规则：Google Types → AI Tags
# ==============================================================================

TYPE_TO_TAGS = {
    # CULTURE tags
    'museum': ['museum'],
    'art_gallery': ['art_gallery'],
    'historical_landmark': ['historical_site'],
    'place_of_worship': ['historical_site'],
    'church': ['historical_site'],
    'landmark': ['urban_landmark', 'instagram_worthy'],
    
    # NATURE tags
    'park': ['national_park'],
    'beach': ['beach'],
    'mountain': ['mountain'],
    
    # FOOD tags
    'restaurant': ['local_cuisine'],
    'cafe': ['cafe'],
    'bakery': ['cafe'],
    'bar': ['nightlife'],
    
    # LEISURE tags
    'shopping_mall': ['shopping'],
    'night_club': ['nightlife'],
    'amusement_park': ['theme_park', 'family_activity'],
    'spa': ['spa_wellness'],
    
    # ADVENTURE tags
    'zoo': ['wildlife', 'kids_friendly'],
    'aquarium': ['wildlife', 'kids_friendly'],
    
    # ROMANTIC tags
    'spa': ['romantic'],
    'lodging': ['romantic', 'resort'],
    
    # FAMILY tags
    'playground': ['kids_friendly', 'family_activity'],
    'amusement_park': ['kids_friendly', 'family_activity'],
    
    # URBAN tags
    'tourist_attraction': ['urban_landmark', 'instagram_worthy'],
    'point_of_interest': ['urban_landmark'],
}

# ==============================================================================
# 基于其他属性的规则
# ==============================================================================

def get_tags_from_price_level(price_level: int, poi_type: str) -> List[str]:
    """根据价格档次推测标签"""
    tags = []
    
    if poi_type == 'restaurant':
        if price_level >= 3:
            tags.append('fine_dining')
        if price_level == 4:
            tags.append('scenic_view')  # 高端餐厅通常环境好
    
    return tags


def get_tags_from_rating(rating: float, review_count: int) -> List[str]:
    """根据评分和评论数推测标签"""
    tags = []
    
    # 高分 + 高评论数 = 打卡圣地
    if rating >= 4.5 and review_count >= 500:
        tags.append('instagram_worthy')
    
    return tags


# ==============================================================================
# AI Prompt 模板
# ==============================================================================

def get_ai_enrichment_prompt(poi_data: Dict, enhanced_details: Dict, table_name: str) -> str:
    """生成 AI 标注的 Prompt"""
    
    available_tags = {
        'restaurants': [
            'michelin', 'fine_dining', 'local_cuisine', 'cafe', 
            'romantic', 'scenic_view', 'instagram_worthy'
        ],
        'attractions': [
            'museum', 'historical_site', 'art_gallery', 'national_park',
            'instagram_worthy', 'kids_friendly', 'family_activity',
            'urban_landmark', 'live_performance'
        ],
        'hotels': [
            'romantic', 'resort', 'spa_wellness', 'kids_friendly', 
            'pet_friendly', 'urban_landmark'
        ]
    }
    
    available_categories = [
        'culture', 'nature', 'food', 'leisure', 
        'adventure', 'romantic', 'family', 'urban'
    ]
    
    review_section = ""
    if enhanced_details.get('review_texts'):
        review_section = "User Reviews Highlights:\n"
        for i, text in enumerate(enhanced_details['review_texts'], 1):
            review_section += f"  {i}. {text}\n"
    
    prompt = f"""You are a professional travel expert analyzing POIs in Paris.

POI Information:
- Name: {poi_data['name']}
- Type: {table_name.rstrip('s')}
- Rating: {poi_data['rating']} ⭐ ({poi_data['review_count']} reviews)
- Price Level: {enhanced_details.get('price_level', 'N/A')}
- Google Description: {enhanced_details.get('editorial_summary') or 'N/A'}

{review_section}

Task:
1. Based on the description and reviews, select 3-5 most relevant AI tags
2. Suggest 1-2 categories that best fit this POI

Available AI Tags for {table_name}:
{', '.join(available_tags.get(table_name, []))}

Available Categories:
{', '.join(available_categories)}

IMPORTANT:
- Use ONLY tags and categories from the available lists above
- Base your selection on the actual reviews and description
- For restaurants: Look for keywords like "michelin", "romantic atmosphere", "scenic view"
- For attractions: Consider if it's family-friendly, has historical significance, or is Instagram-worthy
- For hotels: Look for spa facilities, romantic settings, or family amenities

Return ONLY a JSON object (no markdown, no explanation):
{{
  "ai_tags": ["tag1", "tag2", "tag3"],
  "categories": ["category1", "category2"]
}}
"""
    
    return prompt