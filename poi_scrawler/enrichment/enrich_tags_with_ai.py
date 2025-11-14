"""
使用 AI 为高价值 POI 生成精细标签
筛选标准：
1. 评论数 > 700
2. 评分 > 4.3 且评论数 > 300
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from openai import OpenAI
from typing import List, Dict
import time
import json

from config_enrich import (
    DB_CONFIG, DB_SCHEMA,
    QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL,
    GOOGLE_MAPS_API_KEY,
    HIGH_VALUE_CRITERIA,
    get_ai_enrichment_prompt
)
import googlemaps

# ==============================================================================
# API 客户端
# ==============================================================================

def initialize_clients():
    """初始化 API 客户端"""
    print("🔧 Initializing API clients...")
    
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("   ✅ Google Maps client initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize Google Maps: {e}")
        return None, None
    
    try:
        qwen = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
        print("   ✅ Qwen API client initialized\n")
    except Exception as e:
        print(f"   ❌ Failed to initialize Qwen API: {e}")
        return None, None
    
    return gmaps, qwen


# ==============================================================================
# 数据库操作
# ==============================================================================

def get_high_value_pois_with_missing_tags(conn, table_name: str) -> List[Dict]:
    """
    获取高价值但标签不完整的 POI
    
    标准：
    1. 评论数 > 700
    2. 评分 > 4.3 且评论数 > 300
    """
    
    with conn.cursor() as cursor:
        query = f"""
            SELECT 
                id,
                google_place_id,
                name,
                rating,
                review_count,
                ai_tags,
                categories
            FROM {DB_SCHEMA}.{table_name}
            WHERE 
                (
                    review_count > {HIGH_VALUE_CRITERIA['high_review_threshold']}
                    OR (
                        rating >= {HIGH_VALUE_CRITERIA['quality_rating_threshold']}
                        AND review_count > {HIGH_VALUE_CRITERIA['quality_review_threshold']}
                    )
                )
                AND (
                    ai_tags IS NULL 
                    OR array_length(ai_tags, 1) IS NULL
                    OR array_length(ai_tags, 1) < 3
                )
            ORDER BY review_count DESC
            LIMIT {HIGH_VALUE_CRITERIA['max_pois_per_table']}
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return [{
            'id': row[0],
            'google_place_id': row[1],
            'name': row[2],
            'rating': row[3] or 0,
            'review_count': row[4] or 0,
            'current_tags': row[5] or [],
            'current_categories': row[6] or []
        } for row in rows]


# ==============================================================================
# Google Maps 数据获取
# ==============================================================================

def fetch_enhanced_details(gmaps_client, place_id: str) -> Dict:
    """获取增强信息（评论、介绍）"""
    
    try:
        fields = ['editorial_summary', 'reviews', 'price_level', 'type']
        
        result = gmaps_client.place(place_id=place_id, fields=fields, language='en')
        
        if result.get('status') != 'OK':
            return {}
        
        place = result['result']
        
        # 提取高质量评论
        reviews = place.get('reviews', [])
        review_texts = []
        
        for review in reviews[:5]:  # 最多取5条
            if review.get('rating', 0) >= 4:  # 只要4星及以上
                text = review.get('text', '')
                if text:
                    review_texts.append(text[:200])  # 限制长度
        
        return {
            'editorial_summary': place.get('editorial_summary', {}).get('overview'),
            'review_texts': review_texts,
            'price_level': place.get('price_level'),
            'types': place.get('type', [])
        }
    
    except Exception as e:
        print(f"      ⚠️  Failed to fetch details: {e}")
        return {}


# ==============================================================================
# AI 标注
# ==============================================================================

def generate_tags_with_ai(qwen_client, poi_data: Dict, enhanced_details: Dict, table_name: str) -> Dict:
    """使用 AI 生成精细标签"""
    
    prompt = get_ai_enrichment_prompt(poi_data, enhanced_details, table_name)
    
    try:
        response = qwen_client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": "You are a travel expert. You return only valid JSON without markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
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

def enrich_high_value_pois(conn, table_name: str, gmaps_client, qwen_client):
    """为高价值 POI 做 AI 增强"""
    
    print(f"\n{'='*70}")
    print(f"🌟 AI Enhancement for High-Value {table_name}")
    print(f"{'='*70}")
    print(f"📋 Criteria: review_count > 700 OR (rating > 4.3 AND review_count > 300)\n")
    
    pois = get_high_value_pois_with_missing_tags(conn, table_name)
    
    if not pois:
        print(f"✅ No high-value POIs need enhancement in {table_name}\n")
        return 0
    
    print(f"📋 Found {len(pois)} high-value POIs\n")
    
    updated_count = 0
    failed_count = 0
    
    for i, poi in enumerate(pois, 1):
        print(f"   [{i}/{len(pois)}] 🔍 {poi['name']}")
        print(f"         ⭐ {poi['rating']} | 💬 {poi['review_count']} reviews")
        
        # 获取增强信息
        enhanced_details = fetch_enhanced_details(gmaps_client, poi['google_place_id'])
        
        if not enhanced_details or not enhanced_details.get('review_texts'):
            print(f"         ⚠️  No enhanced details available, skipping...")
            failed_count += 1
            continue
        
        print(f"         📖 Got {len(enhanced_details.get('review_texts', []))} reviews")
        
        # AI 生成标签
        ai_result = generate_tags_with_ai(qwen_client, poi, enhanced_details, table_name)
        
        if not ai_result.get('ai_tags') and not ai_result.get('categories'):
            print(f"         ⚠️  AI returned no tags, skipping...")
            failed_count += 1
            continue
        
        # 合并标签（不覆盖现有标签）
        new_tags = list(set(poi['current_tags'] + ai_result.get('ai_tags', [])))
        new_categories = list(set(poi['current_categories'] + ai_result.get('categories', [])))
        
        # 更新数据库
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE {DB_SCHEMA}.{table_name}
                    SET 
                        ai_tags = %s,
                        categories = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_tags, new_categories, poi['id']))
            
            conn.commit()
            updated_count += 1
            
            print(f"         ✅ Updated!")
            print(f"            Categories: {new_categories}")
            print(f"            Tags: {new_tags[:4]}{'...' if len(new_tags) > 4 else ''}")
        
        except Exception as e:
            print(f"         ❌ Failed to update: {e}")
            failed_count += 1
            conn.rollback()
        
        # 避免 API 限流
        time.sleep(1.5)
    
    print(f"\n📊 Summary for {table_name}:")
    print(f"   ✅ Successfully enhanced: {updated_count}")
    print(f"   ⚠️  Failed/Skipped: {failed_count}")
    
    return updated_count


def main():
    """主流程"""
    
    print("\n" + "="*70)
    print("🤖 AI-Powered Tag Enhancement for High-Value POIs")
    print("="*70 + "\n")
    
    # 初始化客户端
    gmaps_client, qwen_client = initialize_clients()
    
    if not gmaps_client or not qwen_client:
        print("❌ Failed to initialize API clients")
        return 1
    
    # 连接数据库
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connected\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1
    
    total_updated = 0
    
    try:
        for table in ['restaurants', 'attractions', 'hotels']:
            updated = enrich_high_value_pois(conn, table, gmaps_client, qwen_client)
            total_updated += updated
        
        print("\n" + "="*70)
        print(f"✅ SUCCESS! Enhanced {total_updated} high-value POIs across all tables")
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