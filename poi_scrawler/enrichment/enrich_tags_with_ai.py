"""
标签增强：Google Maps API + AI 标注
从数据库读取 → 调用 API 获取详情 → AI 生成标签 → 更新数据库
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from openai import OpenAI
from typing import List, Dict
import time
import json
import googlemaps

from config_enrich import (
    DB_CONFIG, DB_SCHEMA,
    QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL,
    GOOGLE_MAPS_API_KEY,
    get_ai_enrichment_prompt
)

# ==============================================================================
# API 客户端初始化
# ==============================================================================

def initialize_clients():
    """初始化 Google Maps 和 Qwen API 客户端"""
    print("🔧 Initializing API clients...")
    
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("   ✅ Google Maps API initialized")
    except Exception as e:
        print(f"   ❌ Google Maps API failed: {e}")
        return None, None
    
    try:
        qwen = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
        print("   ✅ Qwen API initialized\n")
    except Exception as e:
        print(f"   ❌ Qwen API failed: {e}")
        return None, None
    
    return gmaps, qwen


# ==============================================================================
# 数据库操作
# ==============================================================================

def get_pois_with_missing_tags(conn, table_name: str, limit: int = 50) -> List[Dict]:
    """
    获取需要增强的 POI
    优先处理高价值的（评分高、评论多）
    """
    
    with conn.cursor() as cursor:
        query = f"""
            SELECT 
                id,
                google_place_id,
                name,
                rating,
                review_count,
                price_level,
                ai_tags,
                categories
            FROM {DB_SCHEMA}.{table_name}
            WHERE 
                (ai_tags IS NULL OR array_length(ai_tags, 1) IS NULL OR array_length(ai_tags, 1) < 2)
                OR (categories IS NULL OR array_length(categories, 1) IS NULL OR array_length(categories, 1) = 0)
            ORDER BY 
                review_count DESC,
                rating DESC
            LIMIT {limit}
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return [{
            'id': row[0],
            'google_place_id': row[1],
            'name': row[2],
            'rating': row[3] or 0,
            'review_count': row[4] or 0,
            'price_level': row[5],
            'current_tags': row[6] or [],
            'current_categories': row[7] or []
        } for row in rows]


def update_poi_tags(conn, table_name: str, poi_id: int, tags: List[str], categories: List[str]):
    """更新 POI 的标签和分类"""
    
    with conn.cursor() as cursor:
        cursor.execute(f"""
            UPDATE {DB_SCHEMA}.{table_name}
            SET 
                ai_tags = %s,
                categories = %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (tags, categories, poi_id))


# ==============================================================================
# Google Maps API 调用
# ==============================================================================

def fetch_poi_details(gmaps_client, place_id: str) -> Dict:
    """
    从 Google Maps 获取 POI 详细信息
    包括：types, editorial_summary, reviews, price_level
    """
    
    try:
        # 请求字段
        fields = ['type', 'editorial_summary', 'reviews', 'price_level']
        
        result = gmaps_client.place(place_id=place_id, fields=fields, language='en')
        
        if result.get('status') != 'OK':
            return {}
        
        place = result['result']
        
        # 提取 types（POI 类型）
        types = place.get('type', [])
        
        # 提取 Google 的官方介绍
        editorial_summary = place.get('editorial_summary', {}).get('overview')
        
        # 提取高质量评论（4星及以上）
        reviews = place.get('reviews', [])
        review_texts = []
        for review in reviews[:5]:  # 最多5条
            if review.get('rating', 0) >= 4:
                text = review.get('text', '')
                if text:
                    review_texts.append(text[:200])  # 限制长度
        
        # 提取价格档次
        price_level = place.get('price_level')
        
        return {
            'types': types,
            'editorial_summary': editorial_summary,
            'review_texts': review_texts,
            'price_level': price_level
        }
    
    except Exception as e:
        print(f"      ⚠️  Google Maps API error: {e}")
        return {}


# ==============================================================================
# AI 标注
# ==============================================================================

def generate_tags_with_ai(qwen_client, poi_data: Dict, google_details: Dict, table_name: str) -> Dict:
    """
    使用 Qwen AI 基于 Google 数据生成标签
    """
    
    # 生成 prompt
    prompt = get_ai_enrichment_prompt(poi_data, google_details, table_name)
    
    try:
        response = qwen_client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": "You are a travel expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # 解析响应
        result_text = response.choices[0].message.content.strip()
        
        # 清理 markdown 标记
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(result_text)
        
        return {
            'ai_tags': result.get('ai_tags', []),
            'categories': result.get('categories', [])
        }
    
    except Exception as e:
        print(f"      ⚠️  AI generation failed: {e}")
        return {'ai_tags': [], 'categories': []}


# ==============================================================================
# 主流程
# ==============================================================================

def enrich_table(conn, table_name: str, gmaps_client, qwen_client, limit: int = 50):
    """
    为单个表的 POI 进行标签增强
    """
    
    print(f"\n{'='*70}")
    print(f"📊 Processing {table_name}")
    print(f"{'='*70}")
    
    # 1. 从数据库获取需要增强的 POI
    pois = get_pois_with_missing_tags(conn, table_name, limit)
    
    if not pois:
        print(f"✅ No POIs need enrichment in {table_name}")
        return 0
    
    print(f"📋 Found {len(pois)} POIs to enrich\n")
    
    success_count = 0
    failed_count = 0
    
    for i, poi in enumerate(pois, 1):
        print(f"   [{i}/{len(pois)}] 🔍 {poi['name']}")
        print(f"         ⭐ {poi['rating']} | 💬 {poi['review_count']} reviews")
        
        # 2. 调用 Google Maps API 获取详细信息
        google_details = fetch_poi_details(gmaps_client, poi['google_place_id'])
        
        if not google_details or not google_details.get('types'):
            print(f"         ⚠️  Failed to get Google data, skipping...")
            failed_count += 1
            continue
        
        print(f"         📖 Google types: {google_details['types'][:3]}")
        
        # 3. 使用 AI 生成标签
        ai_result = generate_tags_with_ai(qwen_client, poi, google_details, table_name)
        
        if not ai_result.get('ai_tags') and not ai_result.get('categories'):
            print(f"         ⚠️  AI returned no tags, skipping...")
            failed_count += 1
            continue
        
        # 4. 合并标签（保留原有标签）
        new_tags = list(set(poi['current_tags'] + ai_result.get('ai_tags', [])))
        new_categories = list(set(poi['current_categories'] + ai_result.get('categories', [])))
        
        # 5. 更新数据库
        try:
            update_poi_tags(conn, table_name, poi['id'], new_tags, new_categories)
            conn.commit()
            success_count += 1
            
            print(f"         ✅ Updated!")
            print(f"            Categories: {new_categories}")
            print(f"            Tags: {new_tags[:4]}{'...' if len(new_tags) > 4 else ''}")
        
        except Exception as e:
            print(f"         ❌ Database update failed: {e}")
            conn.rollback()
            failed_count += 1
        
        # 避免 API 限流
        time.sleep(1.5)
    
    print(f"\n📊 Summary for {table_name}:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ⚠️  Failed: {failed_count}")
    
    return success_count


def main():
    """主流程"""
    
    print("\n" + "="*70)
    print("🏷️  POI Tag Enrichment (Google Maps API + AI)")
    print("="*70 + "\n")
    
    # 1. 初始化 API 客户端
    gmaps_client, qwen_client = initialize_clients()
    
    if not gmaps_client or not qwen_client:
        print("❌ Failed to initialize API clients")
        return 1
    
    # 2. 连接数据库
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connected\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1
    
    # 3. 处理三个表
    total_enriched = 0
    
    try:
        for table in ['restaurants', 'attractions', 'hotels']:
            enriched = enrich_table(conn, table, gmaps_client, qwen_client, limit=50)
            total_enriched += enriched
        
        print("\n" + "="*70)
        print(f"✅ SUCCESS! Total enriched: {total_enriched} POIs")
        print("="*70 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        conn.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)