"""
POI 数据爬取模块
合并了 Google API 调用、数据映射和采集逻辑
"""
import googlemaps
import time
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import Config
from .database import Database

class POIScraper:
    """POI 数据爬虫"""
    
    # 搜索关键词
    SEARCH_KEYWORDS = {
        'restaurants': ['restaurant', 'cafe', 'bakery', 'fine dining'],
        'attractions': ['museum', 'attraction', 'landmark', 'monument', 'gallery'],
        'hotels': ['hotel', 'hostel', 'resort', 'accommodation']
    }
    
    # Google Types
    GOOGLE_TYPES = {
        'restaurants': ['restaurant', 'cafe', 'bakery', 'bar'],
        'attractions': ['tourist_attraction', 'museum', 'park', 'art_gallery'],
        'hotels': ['lodging', 'hotel']
    }
    
    def __init__(self, database: Database):
        """初始化爬虫"""
        self.db = database
        
        # 初始化 Google Maps 客户端
        try:
            self.client = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
            self.api_calls_count = 0
            print("✅ Google Maps client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Google Maps client: {e}")
            raise
        
        # 加载分类映射
        self.category_mappings = self.db.get_category_mappings()
        print(f"✅ Loaded {len(self.category_mappings)} category mappings")
        
        # 统计信息
        self.stats = {
            'total_found': 0,
            'new_inserted': 0,
            'existing_updated': 0,
            'failed': 0
        }
    
    def scrape_city(self, city_id: str, poi_type: str = 'all', limit: int = 0) -> Dict[str, Any]:
        """
        爬取指定城市的 POI 数据
        
        Args:
            city_id: 城市 ID
            poi_type: POI 类型 (restaurants/attractions/hotels/all)
            limit: 最大采集数量 (0 = 无限制)
        
        Returns:
            采集统计信息
        """
        start_time = datetime.now()
        
        print("="*80)
        print(f"🚀 Starting POI scraping")
        print(f"   City: {city_id}")
        print(f"   Type: {poi_type}")
        print(f"   Limit: {limit if limit > 0 else 'No limit'}")
        print("="*80 + "\n")
        
        # 获取城市配置
        city_config = self.db.get_city_config(city_id)
        if not city_config:
            error_msg = f"City '{city_id}' not found"
            print(f"❌ {error_msg}")
            return {'status': 'error', 'message': error_msg}
        
        print(f"📍 City: {city_config['city_name']} ({city_config['city_name_cn']})")
        print(f"   Location: ({city_config['latitude']}, {city_config['longitude']})")
        print(f"   Region: {city_config['region']}")
        print(f"   Search radius: {city_config['search_radius']}m\n")
        
        # 确定要采集的类型
        types = ['restaurants', 'attractions', 'hotels'] if poi_type == 'all' else [poi_type]
        
        # 采集每种类型
        for ptype in types:
            print("\n" + "="*80)
            print(f"📦 Scraping {ptype}...")
            print("="*80 + "\n")
            
            try:
                self._scrape_poi_type(city_config, ptype, limit)
            except Exception as e:
                print(f"❌ Failed to scrape {ptype}: {e}")
        
        # 计算执行时间
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 输出统计
        print("\n" + "="*80)
        print("✅ Scraping completed!")
        print("="*80)
        print("📊 Statistics:")
        print(f"   - Total found: {self.stats['total_found']}")
        print(f"   - New inserted: {self.stats['new_inserted']}")
        print(f"   - Existing updated: {self.stats['existing_updated']}")
        print(f"   - Failed: {self.stats['failed']}")
        print(f"   - API calls used: {self.api_calls_count}")
        print(f"   - Execution time: {execution_time:.2f}s")
        print("="*80 + "\n")
        
        return {
            'status': 'success',
            'stats': self.stats,
            'execution_time': execution_time
        }
    
    def _scrape_poi_type(self, city_config: Dict[str, Any], poi_type: str, limit: int) -> None:
        """爬取特定类型的 POI"""
        location = (city_config['latitude'], city_config['longitude'])
        radius = city_config['search_radius']
        region = city_config['region']
        
        all_pois = []
        unique_place_ids = set()
        
        # 1. 按关键词搜索
        keywords = self.SEARCH_KEYWORDS.get(poi_type, [])
        print(f"🔍 Searching with {len(keywords)} keywords...")
        
        for keyword in keywords:
            print(f"   Keyword: '{keyword}'")
            results = self._nearby_search(location, radius, keyword=keyword)
            
            for poi in results:
                place_id = poi.get('place_id')
                if place_id and place_id not in unique_place_ids:
                    unique_place_ids.add(place_id)
                    all_pois.append(poi)
            
            time.sleep(0.5)
            if limit > 0 and len(all_pois) >= limit:
                break
        
        # 2. 按类型搜索
        if limit == 0 or len(all_pois) < limit:
            google_types = self.GOOGLE_TYPES.get(poi_type, [])
            print(f"\n🔍 Searching with {len(google_types)} Google types...")
            
            for gtype in google_types:
                if limit > 0 and len(all_pois) >= limit:
                    break
                
                print(f"   Type: '{gtype}'")
                results = self._nearby_search(location, radius, type=gtype)
                
                for poi in results:
                    place_id = poi.get('place_id')
                    if place_id and place_id not in unique_place_ids:
                        unique_place_ids.add(place_id)
                        all_pois.append(poi)
                
                time.sleep(0.5)
        
        # 限制数量
        if limit > 0:
            all_pois = all_pois[:limit]
        
        print(f"\n📦 Found {len(all_pois)} unique POIs")
        self.stats['total_found'] += len(all_pois)
        
        # 3. 获取详细信息并保存
        if all_pois:
            self._fetch_and_save(all_pois, city_config['city_id'], poi_type, region)
    
    def _nearby_search(
        self,
        location: tuple,
        radius: int,
        keyword: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """附近搜索"""
        all_results = []
        
        try:
            search_params = {'location': location, 'radius': radius}
            if keyword:
                search_params['keyword'] = keyword
            if type:
                search_params['type'] = type
            
            # 第一页
            response = self.client.places_nearby(**search_params)
            self.api_calls_count += 1
            all_results.extend(response.get('results', []))
            
            # 分页
            next_page_token = response.get('next_page_token')
            pages = 1
            
            while next_page_token and pages < 3:
                time.sleep(2)
                try:
                    response = self.client.places_nearby(page_token=next_page_token)
                    self.api_calls_count += 1
                    all_results.extend(response.get('results', []))
                    pages += 1
                    next_page_token = response.get('next_page_token')
                except:
                    break
            
            return all_results
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            return []
    
    def _place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """获取 POI 详细信息"""
        try:
            response = self.client.place(
                place_id=place_id,
                fields=[
                    'place_id', 'name', 'formatted_address',
                    'geometry/location', 'types', 'rating',
                    'user_ratings_total', 'price_level',
                    'opening_hours/open_now', 'opening_hours/weekday_text',
                    'formatted_phone_number', 'international_phone_number',
                    'website', 'photos'
                ]
            )
            
            self.api_calls_count += 1
            time.sleep(Config.REQUEST_DELAY)
            
            return response.get('result')
        except Exception as e:
            print(f"   ❌ Details failed for {place_id}: {e}")
            return None
    
    def _fetch_and_save(
        self,
        pois: List[Dict[str, Any]],
        city_id: str,
        poi_type: str,
        region: str
    ) -> None:
        """获取详细信息并保存"""
        batch = []
        
        print(f"\n💾 Fetching details and saving...")
        
        for i, poi in enumerate(pois, 1):
            place_id = poi.get('place_id')
            poi_name = poi.get('name', 'Unknown')
            
            try:
                if i % 10 == 0 or i == len(pois):
                    print(f"   Progress: [{i}/{len(pois)}] {poi_name[:50]}")
                
                # 获取详细信息
                details = self._place_details(place_id)
                if not details:
                    self.stats['failed'] += 1
                    continue
                
                # 转换数据
                poi_data = self._transform_data(details, city_id, poi_type, region)
                batch.append(poi_data)
                
                # 批量保存
                if len(batch) >= Config.BATCH_SIZE:
                    new_count, updated_count = self.db.bulk_insert_pois(poi_type, batch)
                    self.stats['new_inserted'] += new_count
                    self.stats['existing_updated'] += updated_count
                    batch = []
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.stats['failed'] += 1
        
        # 保存剩余
        if batch:
            new_count, updated_count = self.db.bulk_insert_pois(poi_type, batch)
            self.stats['new_inserted'] += new_count
            self.stats['existing_updated'] += updated_count
    
    def _transform_data(
        self,
        google_data: Dict[str, Any],
        city_id: str,
        poi_type: str,
        region: str
    ) -> Dict[str, Any]:
        """转换 Google 数据为数据库格式"""
        
        # 提取位置
        geometry = google_data.get('geometry', {})
        location = geometry.get('location', {})
        lng = location.get('lng', 0)
        lat = location.get('lat', 0)
        
        # 提取类型
        google_types = google_data.get('types', [])
        
        # 映射分类
        categories = self._map_categories(google_types)
        
        # 映射价格
        google_price_level = google_data.get('price_level')
        price_label = self._map_price(google_price_level) if google_price_level is not None else None
        
        # 提取营业时间
        opening_hours = google_data.get('opening_hours', {})
        opening_hours_data = {
            'open_now': opening_hours.get('open_now'),
            'weekday_text': opening_hours.get('weekday_text', [])
        } if opening_hours else None
        
        # 提取照片
        photos = google_data.get('photos', [])
        photo_urls = []
        primary_photo = None
        
        if photos:
            for photo in photos[:5]:
                ref = photo.get('photo_reference')
                if ref:
                    url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={ref}&key={Config.GOOGLE_MAPS_API_KEY}"
                    photo_urls.append(url)
            
            if photo_urls:
                primary_photo = photo_urls[0]
        
        return {
            'city_id': city_id,
            'google_place_id': google_data.get('place_id', ''),
            'name': google_data.get('name', 'Unknown'),
            'location': f"POINT({lng} {lat})" if lng and lat else None,
            'address': google_data.get('formatted_address', ''),
            'phone': google_data.get('formatted_phone_number') or google_data.get('international_phone_number'),
            'website': google_data.get('website'),
            'rating': google_data.get('rating'),
            'review_count': google_data.get('user_ratings_total', 0),
            'price_level': google_price_level,
            'price_label': price_label,
            'google_types': google_types if google_types else None,
            'categories': categories if categories else None,
            'opening_hours': opening_hours_data,
            'photo_urls': photo_urls if photo_urls else None,
            'primary_photo_url': primary_photo,
            'data_enrichment_level': 'basic',
            'category_source': 'google_types',
            'enrichment_priority': self._calc_priority(google_data.get('rating'), google_data.get('user_ratings_total'))
        }
    
    def _map_categories(self, google_types: List[str]) -> List[str]:
        """映射分类"""
        if not google_types:
            return []
        
        category_scores = {}
        
        for gtype in google_types:
            if gtype in self.category_mappings:
                mapping = self.category_mappings[gtype]
                for cat in mapping['categories']:
                    if cat not in category_scores:
                        category_scores[cat] = 0
                    category_scores[cat] = max(category_scores[cat], mapping['confidence'])
        
        if not category_scores:
            return []
        
        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, score in sorted_cats]
    
    def _map_price(self, google_price_level: int) -> Optional[str]:
        """映射价格等级"""
        if google_price_level == 0:
            return 'free'
        elif google_price_level == 1:
            return 'low'
        elif google_price_level == 2:
            return 'mid'
        elif google_price_level == 3:
            return 'high'
        elif google_price_level == 4:
            return 'luxury'
        return None
    
    def _calc_priority(self, rating: Optional[float], review_count: Optional[int]) -> int:
        """计算优先级"""
        rating = rating or 0
        review_count = review_count or 0
        
        if rating >= 4.5 and review_count >= 100:
            return 10
        elif rating >= 4.5 and review_count >= 50:
            return 9
        elif rating >= 4.0 and review_count >= 100:
            return 8
        elif rating >= 4.0 and review_count >= 50:
            return 7
        elif rating >= 4.0 and review_count >= 20:
            return 6
        elif rating >= 3.5 and review_count >= 50:
            return 5
        elif rating >= 3.5:
            return 4
        elif review_count >= 50:
            return 3
        else:
            return 2


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='TravelNest POI Scraper')
    parser.add_argument('--city-id', required=True, help='City ID')
    parser.add_argument('--poi-type', default='all', choices=['restaurants', 'attractions', 'hotels', 'all'])
    parser.add_argument('--limit', type=int, default=0, help='Max POIs (0=unlimited)')
    
    args = parser.parse_args()
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    try:
        print("="*80)
        print("🚀 Initializing POI Scraper")
        print("="*80)
        
        db = Database()
        if not db.test_connection():
            raise Exception("Database connection failed")
        
        scraper = POIScraper(db)
        
        result = scraper.scrape_city(
            city_id=args.city_id,
            poi_type=args.poi_type,
            limit=args.limit
        )
        
        sys.exit(0 if result['status'] == 'success' else 1)
    
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()