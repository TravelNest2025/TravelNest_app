"""
基于 Google Types 的规则映射
完全免费，不调用任何外部 API
"""
import sys
import os

# 添加父目录到路径以导入 config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from typing import List, Dict, Set
from config_enrich import (
    DB_CONFIG, DB_SCHEMA,
    TYPE_TO_CATEGORIES, TYPE_TO_TAGS,
    get_tags_from_price_level, get_tags_from_rating
)

# ==============================================================================
# 数据库操作
# ==============================================================================

def get_pois_with_missing_tags(conn, table_name: str) -> List[Dict]:
    """获取 tags/categories 为空或不足的 POI"""
    
    with conn.cursor() as cursor:
        query = f"""
            SELECT 
                id, 
                google_place_id, 
                name,
                CAST(google_types AS TEXT) as google_types_json,
                price_level,
                rating,
                review_count,
                ai_tags,
                categories
            FROM {DB_SCHEMA}.{table_name}
            WHERE 
                (ai_tags IS NULL OR array_length(ai_tags, 1) IS NULL OR array_length(ai_tags, 1) = 0)
                OR (categories IS NULL OR array_length(categories, 1) IS NULL OR array_length(categories, 1) = 0)
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        pois = []
        for row in rows:
            import json
            google_types_str = row[3]
            
            # 解析 google_types
            try:
                if google_types_str:
                    # 去除可能的 JSON 转义
                    google_types_str = google_types_str.replace('\\"', '"')
                    google_types = json.loads(google_types_str)
                else:
                    google_types = []
            except Exception as e:
                print(f"      ⚠️  Failed to parse google_types: {e}")
                google_types = []
            
            pois.append({
                'id': row[0],
                'google_place_id': row[1],
                'name': row[2],
                'google_types': google_types,
                'price_level': row[4],
                'rating': row[5] or 0,
                'review_count': row[6] or 0,
                'current_ai_tags': row[7] or [],
                'current_categories': row[8] or []
            })
        
        return pois


def infer_tags_and_categories(poi: Dict, table_name: str) -> Dict:
    """基于 google_types 和其他属性推断 tags 和 categories"""
    
    google_types = poi.get('google_types', [])
    price_level = poi.get('price_level')
    rating = poi.get('rating', 0)
    review_count = poi.get('review_count', 0)
    
    inferred_categories = set()
    inferred_tags = set()
    
    # === 1. 从 Google Types 推断 ===
    for gtype in google_types:
        # 推断 categories
        if gtype in TYPE_TO_CATEGORIES:
            inferred_categories.update(TYPE_TO_CATEGORIES[gtype])
        
        # 推断 tags
        if gtype in TYPE_TO_TAGS:
            inferred_tags.update(TYPE_TO_TAGS[gtype])
    
    # === 2. 从价格档次推断 ===
    if price_level is not None:
        price_tags = get_tags_from_price_level(price_level, table_name.rstrip('s'))
        inferred_tags.update(price_tags)
    
    # === 3. 从评分推断 ===
    rating_tags = get_tags_from_rating(rating, review_count)
    inferred_tags.update(rating_tags)
    
    # === 4. 如果没有推断出任何 category，给默认值 ===
    if not inferred_categories:
        default_categories = {
            'restaurants': ['food'],
            'attractions': ['culture'],
            'hotels': ['romantic']
        }
        inferred_categories.add(default_categories.get(table_name, 'urban'))
    
    return {
        'categories': list(inferred_categories),
        'ai_tags': list(inferred_tags)
    }


def update_poi_tags(conn, table_name: str, poi_id: int, tags: List[str], categories: List[str]):
    """更新单个 POI 的 tags 和 categories"""
    
    with conn.cursor() as cursor:
        # 只更新为空的字段
        query = f"""
            UPDATE {DB_SCHEMA}.{table_name}
            SET 
                ai_tags = CASE 
                    WHEN ai_tags IS NULL OR array_length(ai_tags, 1) IS NULL OR array_length(ai_tags, 1) = 0
                    THEN %s 
                    ELSE ai_tags 
                END,
                categories = CASE 
                    WHEN categories IS NULL OR array_length(categories, 1) IS NULL OR array_length(categories, 1) = 0
                    THEN %s 
                    ELSE categories 
                END,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        
        cursor.execute(query, (tags, categories, poi_id))


# ==============================================================================
# 主流程
# ==============================================================================

def enrich_table(conn, table_name: str):
    """为单个表填充标签"""
    
    print(f"\n{'='*70}")
    print(f"📊 Processing {table_name}")
    print(f"{'='*70}")
    
    # 获取空白 POI
    pois = get_pois_with_missing_tags(conn, table_name)
    
    if not pois:
        print(f"✅ No POIs with missing tags in {table_name}")
        return
    
    print(f"📋 Found {len(pois)} POIs with missing tags/categories\n")
    
    updated_count = 0
    
    for poi in pois:
        # 推断标签
        inferred = infer_tags_and_categories(poi, table_name)
        
        # 合并现有标签（不覆盖）
        final_tags = list(set(poi['current_ai_tags'] + inferred['ai_tags']))
        final_categories = list(set(poi['current_categories'] + inferred['categories']))
        
        # 只在有新标签时更新
        if final_tags != poi['current_ai_tags'] or final_categories != poi['current_categories']:
            update_poi_tags(conn, table_name, poi['id'], final_tags, final_categories)
            updated_count += 1
            
            print(f"   ✅ {poi['name']}")
            print(f"      Google Types: {poi['google_types'][:3]}{'...' if len(poi['google_types']) > 3 else ''}")
            print(f"      → Categories: {final_categories}")
            print(f"      → Tags: {final_tags[:3]}{'...' if len(final_tags) > 3 else ''}")
    
    conn.commit()
    
    print(f"\n✅ Updated {updated_count}/{len(pois)} POIs in {table_name}")


def main():
    """主流程"""
    
    print("\n" + "="*70)
    print("🏷️  Tag Enrichment from Google Types (Rule-Based)")
    print("="*70 + "\n")
    
    # 连接数据库
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connected\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1
    
    try:
        # 处理三个表
        for table in ['restaurants', 'attractions', 'hotels']:
            enrich_table(conn, table)
        
        print("\n" + "="*70)
        print("✅ SUCCESS! All tables enriched with rule-based tags")
        print("="*70 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)