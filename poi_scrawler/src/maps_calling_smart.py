"""
智能POI数据获取和去重模块
策略：先爬取150个 → 验证和去重 → 补充到200个
"""
import os
import json
import time
import googlemaps
from openai import OpenAI
from collections import defaultdict
from typing import List, Dict, Optional, Set, Tuple
from math import radians, cos, sin, asin, sqrt

# 导入配置
from config import (
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
    GOOGLE_MAPS_API_KEY,
    TARGET_CITY,
    CITY_ID,
    AI_BATCH_SIZE,
    SEARCH_KEYWORDS,
    get_ai_prompt,
    validate_config
)

# ==============================================================================
# 配置常量
# ==============================================================================

# 目标POI数量
TARGET_POI_COUNT = 300

# 第一轮采集数量（比目标数多采集25%作为缓冲）
INITIAL_COLLECTION_COUNT = 225

# 每个关键词搜索的POI数量
POIS_PER_KEYWORD_INITIAL = 20  # 第一轮：每个关键词20个
POIS_PER_KEYWORD_SUPPLEMENT = 10  # 补充轮：每个关键词10个

# 去重参数
MIN_DISTANCE_METERS = 10  # 最小距离阈值（米），同一地点的不同入口
SIMILARITY_THRESHOLD = 0.95  # 名称相似度阈值


# ==============================================================================
# 辅助函数
# ==============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两个经纬度坐标之间的距离（米）
    使用Haversine公式
    """
    # 转换为弧度
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # 地球半径（米）
    r = 6371000
    
    return c * r


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    计算两个名称的相似度（简单的Jaccard相似度）
    """
    # 转换为小写并分词
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    
    # 计算Jaccard相似度
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def is_duplicate(poi: Dict, existing_pois: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    检查POI是否与已有POI重复
    
    Returns:
        (是否重复, 重复原因)
    """
    poi_location = poi.get('location', {})
    poi_lat = poi_location.get('lat')
    poi_lng = poi_location.get('lng')
    poi_name = poi.get('name', '')
    
    if not poi_lat or not poi_lng:
        return True, "缺少地理坐标"
    
    for existing in existing_pois:
        # 检查Place ID是否相同
        if poi.get('google_place_id') == existing.get('google_place_id'):
            return True, f"Place ID重复: {existing.get('name')}"
        
        # 检查地理位置是否过近
        existing_location = existing.get('location', {})
        existing_lat = existing_location.get('lat')
        existing_lng = existing_location.get('lng')
        
        if existing_lat and existing_lng:
            distance = haversine_distance(poi_lat, poi_lng, existing_lat, existing_lng)
            
            if distance < MIN_DISTANCE_METERS:
                # 距离很近，再检查名称相似度
                similarity = calculate_name_similarity(poi_name, existing.get('name', ''))
                
                if similarity > SIMILARITY_THRESHOLD:
                    return True, f"地理位置重复({distance:.1f}m) + 名称相似({similarity:.2f}): {existing.get('name')}"
    
    return False, None


# ==============================================================================
# 初始化客户端
# ==============================================================================

def initialize_clients():
    """初始化Google Maps和Qwen API客户端"""
    print("🔧 Initializing API clients...")
    
    try:
        gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("✅ Google Maps client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Google Maps client: {e}")
        return None, None
    
    try:
        qwen_client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
        print("✅ Qwen API client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Qwen client: {e}")
        print(f"   Error details: {str(e)}")
        return None, None
    
    return gmaps_client, qwen_client


# ==============================================================================
# Google Maps数据获取
# ==============================================================================

def fetch_place_details(gmaps_client, place_id: str) -> Optional[Dict]:
    """获取单个地点的详细信息"""
    try:
        fields = [
            'place_id', 'name', 'formatted_address', 'geometry',
            'rating', 'user_ratings_total', 'website',
            'international_phone_number', 'opening_hours',
            'price_level', 'photo', 'type', 'business_status',
            'editorial_summary',  # ← 新增：Google 的介绍
            'reviews',            # ← 新增：用户评论
            'types'
        ]
        
        result = gmaps_client.place(place_id=place_id, fields=fields, language='en')
        
        if result.get('status') != 'OK':
            return None
        
        place = result['result']
        
        # 提取评论摘要（前5条）
        review_summaries = []
        reviews = place.get('reviews', [])
        for review in reviews[:5]:  # 只取前5条
            review_summaries.append({
                'rating': review.get('rating'),
                'text': review.get('text', '')[:200]  # 限制长度
            })

        # 提取照片URL
        photo_urls = []
        photos = place.get('photo', [])  # ✅
        if photos:
            for photo in photos[:5]:
                photo_reference = photo['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1600&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                photo_urls.append(photo_url)
        
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
            "google_types": place.get('type', []),
            "business_status": place.get('business_status', 'OPERATIONAL'),
            "editorial_summary": place.get('editorial_summary', {}).get('overview'),
            "review_summaries": review_summaries,
            "price_level": place.get('price_level'),  # 0-4（免费到很贵）
            "types": place.get('types', [])  # 完整类型列表
        }
    
    except Exception as e:
        print(f"❌ Error fetching details for place_id {place_id}: {e}")
        return None


def search_pois_by_keyword(gmaps_client, city: str, keyword: str, limit: int) -> List[str]:
    """使用关键词搜索POI，返回Place ID列表"""
    try:
        query = f"{keyword} in {city}"
        results = gmaps_client.places(query=query, language='en')
        
        if results.get('status') != 'OK':
            return []
        
        place_ids = [place['place_id'] for place in results.get('results', [])[:limit]]
        return place_ids
    
    except Exception as e:
        print(f"❌ Error searching for '{keyword}': {e}")
        return []


def collect_pois_round(gmaps_client, poi_type: str, keywords: List[str], 
                       limit_per_keyword: int, existing_pois: List[Dict]) -> List[Dict]:
    """
    执行一轮POI采集
    
    Args:
        gmaps_client: Google Maps客户端
        poi_type: POI类型
        keywords: 搜索关键词列表
        limit_per_keyword: 每个关键词的POI数量限制
        existing_pois: 已存在的POI列表（用于去重）
    
    Returns:
        新采集的POI列表
    """
    new_pois = []
    collected_place_ids = set()
    
    for keyword in keywords:
        print(f"  🔍 Searching for '{keyword}'...")
        
        place_ids = search_pois_by_keyword(gmaps_client, TARGET_CITY, keyword, limit_per_keyword)
        
        for place_id in place_ids:
            # 跳过已采集的Place ID
            if place_id in collected_place_ids:
                continue
            
            # 获取详细信息
            details = fetch_place_details(gmaps_client, place_id)
            
            if not details:
                continue
            
            # 过滤永久关闭的POI
            if details['business_status'] == 'CLOSED_PERMANENTLY':
                continue
            
            # 检查是否与已有POI重复
            is_dup, reason = is_duplicate(details, existing_pois + new_pois)
            
            if is_dup:
                print(f"    ⚠️  Skipping duplicate: {details['name']} ({reason})")
                continue
            
            # 添加POI类型标记
            details['poi_type'] = poi_type
            details['city_id'] = CITY_ID
            
            new_pois.append(details)
            collected_place_ids.add(place_id)
            
            print(f"    ✅ Collected: {details['name']}")
            
            time.sleep(0.3)
        
        time.sleep(0.5)
    
    return new_pois


# ==============================================================================
# AI增强
# ==============================================================================

def enrich_pois_with_ai(qwen_client, poi_list: List[Dict], poi_type: str) -> List[Dict]:
    """使用Qwen AI为POI批量添加标签和补充信息"""
    if not poi_list:
        return []
    
    print(f"\n🤖 AI Enhancement for {len(poi_list)} {poi_type} POIs...")
    
    batches = [poi_list[i:i + AI_BATCH_SIZE] for i in range(0, len(poi_list), AI_BATCH_SIZE)]
    enriched_pois = []
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"  Batch {batch_idx}/{len(batches)} ({len(batch)} POIs)...")
        
        try:
            prompt = get_ai_prompt(poi_type, batch)
            
            response = qwen_client.chat.completions.create(
                model=QWEN_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional travel data analyst. You provide structured JSON output."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            ai_response_text = response.choices[0].message.content.strip()
            
            # 清理markdown标记
            ai_response_text = ai_response_text.replace("```json", "").replace("```", "").strip()
            
            ai_results = json.loads(ai_response_text)
            enriched_data = ai_results.get('enriched_data', [])
            
            enrichment_map = {item['name']: item for item in enriched_data}
            
            for poi in batch:
                poi_name = poi['name']
                if poi_name in enrichment_map:
                    poi.update(enrichment_map[poi_name])
            
            enriched_pois.extend(batch)
            
            time.sleep(1)
        
        except Exception as e:
            print(f"  ❌ Error processing batch {batch_idx}: {e}")
            enriched_pois.extend(batch)
    
    return enriched_pois


# ==============================================================================
# 主流程
# ==============================================================================

def main():
    """主执行流程 - 方案B：清晰两阶段"""
    print("\n" + "="*70)
    print("🌍 Smart POI Data Collection Pipeline")
    print("="*70 + "\n")
    
    # 验证配置
    if not validate_config(require_db=False):
        print("\n❌ Configuration validation failed. Exiting...")
        return
    
    # 初始化客户端
    gmaps_client, qwen_client = initialize_clients()
    if not gmaps_client:
        print("\n❌ Google Maps client initialization failed. Exiting...")
        return
    
    # ========================================================================
    # PHASE 1: 数据采集
    # ========================================================================
    
    raw_data_file = f"{CITY_ID}_raw_pois.json"
    
    if os.path.exists(raw_data_file) and os.environ.get('SKIP_COLLECTION') == 'true':
        print("="*70)
        print("⏭️  SKIPPING PHASE 1: Using existing raw data")
        print("="*70 + "\n")
        
        with open(raw_data_file, 'r', encoding='utf-8') as f:
            all_raw_pois = json.load(f)
        
        print(f"✅ Loaded {len(all_raw_pois)} POIs from {raw_data_file}")
    else:
        print("="*70)
        print("📥 PHASE 1: DATA COLLECTION")
        print("="*70 + "\n")
        
        # 调用你原有的采集逻辑
        all_pois_by_type = defaultdict(list)
        
        target_per_type = INITIAL_COLLECTION_COUNT // 3
        
        for poi_type, keywords in SEARCH_KEYWORDS.items():
            print(f"\n--- {poi_type.upper()} (Target: {target_per_type}) ---")
            
            collected = collect_pois_round(
                gmaps_client=gmaps_client,
                poi_type=poi_type,
                keywords=keywords,
                limit_per_keyword=POIS_PER_KEYWORD_INITIAL,
                existing_pois=[]
            )
            
            all_pois_by_type[poi_type].extend(collected)
            print(f"   ✅ Collected {len(collected)} {poi_type} POIs")
        
        phase1_total = sum(len(pois) for pois in all_pois_by_type.values())
        
        # 补充采集（如果需要）
        if phase1_total < TARGET_POI_COUNT:
            shortage = TARGET_POI_COUNT - phase1_total
            print(f"\n📥 Supplemental Collection (Need {shortage} more POIs)\n")
            
            for poi_type, keywords in SEARCH_KEYWORDS.items():
                current_count = len(all_pois_by_type[poi_type])
                target_count = TARGET_POI_COUNT // 3
                
                if current_count >= target_count:
                    continue
                
                needed = target_count - current_count
                print(f"--- {poi_type.upper()}: Need {needed} more ---")
                
                supplemented = collect_pois_round(
                    gmaps_client=gmaps_client,
                    poi_type=poi_type,
                    keywords=keywords,
                    limit_per_keyword=POIS_PER_KEYWORD_SUPPLEMENT * 2,
                    existing_pois=all_pois_by_type[poi_type]
                )
                
                all_pois_by_type[poi_type].extend(supplemented)
                print(f"   ✅ Supplemented {len(supplemented)} {poi_type} POIs")
        
        # 合并为一个列表
        all_raw_pois = []
        for pois in all_pois_by_type.values():
            all_raw_pois.extend(pois)
        
        # 保存原始数据（检查点）
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(all_raw_pois, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Phase 1 Complete: {len(all_raw_pois)} POIs saved to {raw_data_file}")
    
    # ========================================================================
    # PHASE 2: AI增强
    # ========================================================================
    
    if os.environ.get('SKIP_AI_ENHANCEMENT') == 'true':
        print("\n⏭️  SKIPPING PHASE 2: AI Enhancement\n")
        final_pois = all_raw_pois
    else:
        if not qwen_client:
            print("\n⚠️  Qwen client not available, skipping AI enhancement\n")
            final_pois = all_raw_pois
        else:
            print("\n" + "="*70)
            print("🤖 PHASE 2: AI ENHANCEMENT")
            print("="*70 + "\n")
            
            # 按类型分组
            grouped = defaultdict(list)
            for poi in all_raw_pois:
                grouped[poi['poi_type']].append(poi)
            
            final_pois = []
            
            for poi_type, poi_list in grouped.items():
                enriched = enrich_pois_with_ai(qwen_client, poi_list, poi_type)
                final_pois.extend(enriched)
    
    # ========================================================================
    # 保存最终结果
    # ========================================================================
    
    output_filename = f"{CITY_ID}_comprehensive_database.json"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(final_pois, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ SUCCESS!")
    print(f"{'='*70}")
    print(f"📁 Output file: {output_filename}")
    print(f"📊 Final Statistics:")
    print(f"   - Total POIs: {len(final_pois)}")
    
    by_type = defaultdict(int)
    for poi in final_pois:
        by_type[poi.get('poi_type', 'unknown')] += 1
    
    for poi_type, count in by_type.items():
        print(f"   - {poi_type.capitalize()}: {count}")
    
    print(f"   - Target Achievement: {len(final_pois)}/{TARGET_POI_COUNT} ({len(final_pois)/TARGET_POI_COUNT*100:.1f}%)")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()