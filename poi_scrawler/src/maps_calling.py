"""
POI数据获取和AI增强模块
从Google Maps获取POI数据，使用阿里云Qwen进行AI标注
"""
import os
import json
import time
import googlemaps
from openai import OpenAI
from collections import defaultdict
from typing import List, Dict, Optional

# 导入配置
from config import (
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
    GOOGLE_MAPS_API_KEY,
    TARGET_CITY,
    CITY_ID,
    AI_BATCH_SIZE,
    POIS_PER_KEYWORD,
    SEARCH_KEYWORDS,
    get_ai_prompt,
    validate_config
)

# ==============================================================================
# 初始化客户端
# ==============================================================================

def initialize_clients():
    """初始化Google Maps和Qwen API客户端"""
    
    print("🔧 Initializing API clients...")
    
    # Google Maps客户端
    try:
        gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("✅ Google Maps client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Google Maps client: {e}")
        return None, None
    
    # Qwen客户端 (使用OpenAI SDK)
    try:
        qwen_client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL
        )
        print("✅ Qwen API client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Qwen client: {e}")
        return None, None
    
    return gmaps_client, qwen_client


# ==============================================================================
# Google Maps数据获取
# ==============================================================================

def fetch_place_details(gmaps_client, place_id: str) -> Optional[Dict]:
    """
    获取单个地点的详细信息
    
    Args:
        gmaps_client: Google Maps客户端
        place_id: Google Place ID
    
    Returns:
        包含详细信息的字典，失败返回None
    """
    try:
        fields = [
            'place_id', 'name', 'formatted_address', 'geometry',
            'rating', 'user_ratings_total', 'website',
            'international_phone_number', 'opening_hours',
            'price_level', 'photos', 'types', 'business_status'
        ]
        
        result = gmaps_client.place(
            place_id=place_id,
            fields=fields,
            language='en'
        )
        
        if result.get('status') != 'OK':
            print(f"⚠️  Place details request failed: {result.get('status')}")
            return None
        
        place = result['result']
        
        # 提取照片URL
        photo_urls = []
        if 'photos' in place:
            for photo in place['photos'][:5]:  # 最多5张照片
                photo_reference = photo['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1600&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                photo_urls.append(photo_url)
        
        # 提取地理坐标
        location = place.get('geometry', {}).get('location', {})
        
        return {
            "google_place_id": place.get('place_id'),
            "name": place.get('name'),
            "address": place.get('formatted_address'),
            "location": {
                "lat": location.get('lat'),
                "lng": location.get('lng')
            },
            "rating": place.get('rating', 0),
            "review_count": place.get('user_ratings_total', 0),
            "website": place.get('website'),
            "phone": place.get('international_phone_number'),
            "opening_hours": place.get('opening_hours'),
            "price_level": place.get('price_level'),
            "photo_urls": photo_urls,
            "primary_photo_url": photo_urls[0] if photo_urls else None,
            "google_types": place.get('types', []),
            "business_status": place.get('business_status', 'OPERATIONAL')
        }
    
    except Exception as e:
        print(f"❌ Error fetching details for place_id {place_id}: {e}")
        return None


def search_pois_by_keyword(gmaps_client, city: str, keyword: str, limit: int = POIS_PER_KEYWORD) -> List[str]:
    """
    使用关键词搜索POI，返回Place ID列表
    
    Args:
        gmaps_client: Google Maps客户端
        city: 城市名称
        keyword: 搜索关键词
        limit: 返回结果数量限制
    
    Returns:
        Place ID列表
    """
    print(f"🔍 Searching for '{keyword}' in {city}...")
    
    try:
        query = f"{keyword} in {city}"
        results = gmaps_client.places(query=query, language='en')
        
        if results.get('status') != 'OK':
            print(f"⚠️  Search failed: {results.get('status')}")
            return []
        
        place_ids = [
            place['place_id']
            for place in results.get('results', [])[:limit]
        ]
        
        print(f"✅ Found {len(place_ids)} POIs for '{keyword}'")
        return place_ids
    
    except Exception as e:
        print(f"❌ Error searching for '{keyword}': {e}")
        return []


def fetch_all_pois(gmaps_client) -> Dict[str, List[Dict]]:
    """
    获取所有类型POI的详细信息
    
    Returns:
        按类型分组的POI字典 {'restaurant': [...], 'attraction': [...], 'hotel': [...]}
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting POI data collection for {TARGET_CITY}")
    print(f"{'='*60}\n")
    
    all_place_ids = defaultdict(set)
    
    # 第1步：按关键词搜索，收集所有Place ID
    for poi_type, keywords in SEARCH_KEYWORDS.items():
        print(f"\n--- Collecting {poi_type.upper()} POIs ---")
        
        for keyword in keywords:
            place_ids = search_pois_by_keyword(gmaps_client, TARGET_CITY, keyword)
            all_place_ids[poi_type].update(place_ids)
            
            # 避免API速率限制
            time.sleep(0.5)
        
        print(f"📊 Total unique {poi_type} POIs: {len(all_place_ids[poi_type])}")
    
    # 第2步：获取每个POI的详细信息
    grouped_pois = defaultdict(list)
    
    for poi_type, place_ids in all_place_ids.items():
        print(f"\n--- Fetching details for {len(place_ids)} {poi_type} POIs ---")
        
        for i, place_id in enumerate(place_ids, 1):
            print(f"[{i}/{len(place_ids)}] Fetching details for {place_id}...")
            
            details = fetch_place_details(gmaps_client, place_id)
            
            if details:
                # 添加POI类型标记
                details['poi_type'] = poi_type
                details['city_id'] = CITY_ID
                
                # 过滤永久关闭的POI
                if details['business_status'] == 'CLOSED_PERMANENTLY':
                    print(f"⚠️  Skipping permanently closed POI: {details['name']}")
                    continue
                
                grouped_pois[poi_type].append(details)
            
            # 避免API速率限制
            time.sleep(0.3)
    
    # 打印统计
    print(f"\n{'='*60}")
    print("📊 Data Collection Summary:")
    print(f"{'='*60}")
    for poi_type, pois in grouped_pois.items():
        print(f"  {poi_type.capitalize()}: {len(pois)} POIs")
    print(f"  Total: {sum(len(pois) for pois in grouped_pois.values())} POIs")
    print(f"{'='*60}\n")
    
    return dict(grouped_pois)


# ==============================================================================
# AI增强 (使用阿里云Qwen)
# ==============================================================================

def enrich_pois_with_ai(qwen_client, poi_list: List[Dict], poi_type: str) -> List[Dict]:
    """
    使用Qwen AI为POI批量添加标签和补充信息
    
    Args:
        qwen_client: Qwen API客户端
        poi_list: POI列表
        poi_type: POI类型
    
    Returns:
        增强后的POI列表
    """
    if not poi_list:
        return []
    
    print(f"\n🤖 AI Enhancement for {len(poi_list)} {poi_type} POIs...")
    print(f"   Using model: {QWEN_MODEL}")
    print(f"   Batch size: {AI_BATCH_SIZE}")
    
    # 分批处理
    batches = [
        poi_list[i:i + AI_BATCH_SIZE]
        for i in range(0, len(poi_list), AI_BATCH_SIZE)
    ]
    
    enriched_pois = []
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n--- Processing Batch {batch_idx}/{len(batches)} ({len(batch)} POIs) ---")
        
        try:
            # 生成Prompt
            prompt = get_ai_prompt(poi_type, batch)
            
            # 调用Qwen API
            print("📡 Calling Qwen API...")
            response = qwen_client.chat.completions.create(
                model=QWEN_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional travel data analyst. You provide structured JSON output."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # 解析响应
            ai_response_text = response.choices[0].message.content.strip()
            
            # 移除可能的markdown代码块标记
            if ai_response_text.startswith("```json"):
                ai_response_text = ai_response_text[7:]
            if ai_response_text.startswith("```"):
                ai_response_text = ai_response_text[3:]
            if ai_response_text.endswith("```"):
                ai_response_text = ai_response_text[:-3]
            ai_response_text = ai_response_text.strip()
            
            # 解析JSON
            ai_results = json.loads(ai_response_text)
            enriched_data = ai_results.get('enriched_data', [])
            
            # 验证返回数量
            if len(enriched_data) != len(batch):
                print(f"⚠️  Warning: Expected {len(batch)} results, got {len(enriched_data)}")
            
            # 将AI结果合并回原POI
            enrichment_map = {item['name']: item for item in enriched_data}
            
            for poi in batch:
                poi_name = poi['name']
                if poi_name in enrichment_map:
                    ai_data = enrichment_map[poi_name]
                    poi.update(ai_data)
                    print(f"✅ Enhanced: {poi_name}")
                else:
                    print(f"⚠️  No AI data for: {poi_name}")
            
            enriched_pois.extend(batch)
            
            # 显示API使用情况
            print(f"📊 Tokens used: {response.usage.total_tokens}")
            print(f"   - Prompt: {response.usage.prompt_tokens}")
            print(f"   - Completion: {response.usage.completion_tokens}")
            
            # 避免API速率限制
            time.sleep(1)
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error in batch {batch_idx}: {e}")
            print(f"Response text: {ai_response_text[:500]}...")
            # 将未增强的批次也加入结果
            enriched_pois.extend(batch)
        
        except Exception as e:
            print(f"❌ Error processing batch {batch_idx}: {e}")
            # 将未增强的批次也加入结果
            enriched_pois.extend(batch)
    
    print(f"\n✅ AI enhancement completed for {len(enriched_pois)} POIs")
    return enriched_pois


# ==============================================================================
# 主流程
# ==============================================================================

def main():
    """主执行流程"""
    print("\n" + "="*60)
    print("🌍 POI Data Collection Pipeline - Starting")
    print("="*60 + "\n")
    
    # 验证配置
    if not validate_config():
        print("\n❌ Configuration validation failed. Exiting...")
        return
    
    # 初始化客户端
    gmaps_client, qwen_client = initialize_clients()
    if not gmaps_client or not qwen_client:
        print("\n❌ Client initialization failed. Exiting...")
        return
    
    # 第1步：从Google Maps获取POI数据
    grouped_pois = fetch_all_pois(gmaps_client)
    
    # 第2步：使用AI增强每个类型的POI
    all_enriched_pois = []
    
    for poi_type, pois in grouped_pois.items():
        if not pois:
            continue
        
        enriched = enrich_pois_with_ai(qwen_client, pois, poi_type)
        all_enriched_pois.extend(enriched)
    
    # 第3步：保存到文件
    output_filename = f"{CITY_ID}_comprehensive_database.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_enriched_pois, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS!")
        print(f"{'='*60}")
        print(f"📁 Output file: {output_filename}")
        print(f"📊 Total POIs: {len(all_enriched_pois)}")
        print(f"   - Restaurants: {sum(1 for p in all_enriched_pois if p.get('poi_type') == 'restaurant')}")
        print(f"   - Attractions: {sum(1 for p in all_enriched_pois if p.get('poi_type') == 'attraction')}")
        print(f"   - Hotels: {sum(1 for p in all_enriched_pois if p.get('poi_type') == 'hotel')}")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"\n❌ Error saving output file: {e}")


if __name__ == "__main__":
    main()