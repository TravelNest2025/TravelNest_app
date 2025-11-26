"""
Google Places Type 到 Categories 的映射

根据Google Places API的类型，映射到我们的7大主分类和24个标签。

分类说明：
- 5个主分类: culture, nature, food, leisure, adventure
- 2个辅助分类: romantic, family (仅用于标签，不用于POI主分类)

映射优先级：
1. 餐厅类型 → food
2. 景点类型 → culture/nature/leisure/adventure
3. 酒店类型 → leisure (酒店不设置主分类，仅用于区分POI类型)

映射策略：
- 优先从数据库 google_type_category_mapping 表读取
- 数据库读取失败时，使用硬编码规则作为fallback
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ==========================================
# 数据库映射查询（主要方案）
# ==========================================

def map_types_to_categories_from_db(
    google_types: list[str],
    supabase_client = None
) -> list[str]:
    """
    从数据库 google_type_category_mapping 表批量查询映射规则
    
    使用 IN 查询一次性获取所有映射，避免多次数据库查询。
    
    Args:
        google_types: Google Places API返回的类型列表
        supabase_client: Supabase客户端（必需）
        
    Returns:
        分类列表，如['food', 'culture']；无匹配时返回空列表[]
    """
    if supabase_client is None:
        logger.error("❌ Supabase客户端未提供，无法查询映射")
        return []
    
    if not google_types:
        return []
    
    categories = set()
    
    try:
        # 使用 IN 查询一次性获取所有映射
        result = supabase_client.table('google_type_category_mapping').select(
            'google_type, mapped_categories'
        ).in_('google_type', google_types).eq('is_active', True).execute()
        
        if result.data:
            # 合并所有匹配的categories
            for row in result.data:
                mapped = row['mapped_categories']
                categories.update(mapped)
                logger.debug(f"✅ 映射: {row['google_type']} → {mapped}")
            
            logger.info(f"📊 批量查询成功: 匹配 {len(result.data)}/{len(google_types)} 个类型")
        else:
            logger.warning(f"⚠️  数据库中无匹配: {google_types}")
    
    except Exception as e:
        logger.error(f"❌ 批量查询失败: {e}")
        return []
    
    # 只保留主分类（排除romantic和family，这两个仅用于Phase 2 AI tags）
    main_categories = {'culture', 'nature', 'food', 'leisure', 'adventure'}
    result = list(categories & main_categories)
    
    # 无匹配时返回空列表（不使用兜底值）
    if not result:
        logger.info(f"⚠️  无主分类匹配: {google_types} → 返回空列表")
        return []
    
    logger.info(f"📊 最终映射: {google_types} → {result}")
    return result


def get_auxiliary_tags_from_db(
    google_types: list[str],
    supabase_client = None
) -> list[str]:
    """
    从数据库批量获取辅助标签（romantic、family）
    
    这些标签不作为主分类，仅供Phase 2 AI标注时参考。
    
    Args:
        google_types: Google Places API返回的类型列表
        supabase_client: Supabase客户端
        
    Returns:
        辅助标签列表，如['romantic', 'family']；无匹配时返回[]
    """
    if supabase_client is None or not google_types:
        return []
    
    auxiliary_tags = set()
    
    try:
        # 使用 IN 查询批量获取
        result = supabase_client.table('google_type_category_mapping').select(
            'google_type, mapped_categories'
        ).in_('google_type', google_types).eq('is_active', True).execute()
        
        if result.data:
            for row in result.data:
                mapped = row['mapped_categories']
                # 只提取辅助标签
                for tag in mapped:
                    if tag in ['romantic', 'family']:
                        auxiliary_tags.add(tag)
    
    except Exception as e:
        logger.debug(f"查询辅助标签失败: {e}")
    
    return list(auxiliary_tags)


# ==========================================
# POI类型判定规则
# ==========================================

RESTAURANT_TYPES = {
    'restaurant',
    'cafe',
    'bar',
    'bakery',
    'meal_takeaway',
    'meal_delivery',
    'food',
    'bistro',
    'brasserie',
}

ATTRACTION_TYPES = {
    'tourist_attraction',
    'museum',
    'art_gallery',
    'church',
    'park',
    'point_of_interest',
    'premise',
    'establishment',
    'amusement_park',
    'aquarium',
    'zoo',
    'stadium',
    'movie_theater',
    'night_club',
    'casino',
    'shopping_mall',
    'store',
    'library',
    'university',
    'landmark',
}

HOTEL_TYPES = {
    'lodging',
    'hotel',
    'hostel',
    'guest_house',
    'resort',
}


def determine_poi_type(google_types: list[str]) -> str:
    """
    根据Google返回的多个类型，判定POI的主要类型
    
    优先级：餐厅 > 酒店 > 景点
    
    Args:
        google_types: Google Places API返回的类型列表
        
    Returns:
        'restaurant' | 'attraction' | 'hotel'
    """
    types_set = set(google_types)
    
    # 优先判定餐厅
    if types_set & RESTAURANT_TYPES:
        return 'restaurant'
    
    # 其次判定酒店
    if types_set & HOTEL_TYPES:
        return 'hotel'
    
    # 最后判定景点
    if types_set & ATTRACTION_TYPES:
        return 'attraction'
    
    # 兜底：默认为景点
    return 'attraction'


# ==========================================
# 测试用例
# ==========================================

if __name__ == '__main__':
    # 测试POI类型判定
    test_cases = [
        (['restaurant', 'food', 'point_of_interest'], 'restaurant'),
        (['lodging', 'hotel', 'point_of_interest'], 'hotel'),
        (['museum', 'tourist_attraction', 'point_of_interest'], 'attraction'),
        (['park', 'point_of_interest'], 'attraction'),
        (['store', 'shopping_mall'], 'attraction'),  # 兜底
    ]
    
    print("=== POI类型判定测试 ===")
    for google_types, expected in test_cases:
        result = determine_poi_type(google_types)
        status = '✅' if result == expected else '❌'
        print(f"{status} {google_types} → {result} (期望: {expected})")
    
    print("\n=== 所有测试完成 ===")