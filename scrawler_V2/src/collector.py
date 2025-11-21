"""
POI 数据采集主模块
"""
import argparse
import time
import sys
from datetime import datetime
from typing import List, Dict, Any

from .config import Config
from .database import Database
from .google_places_client import GooglePlacesClient
from .poi_mapper import POIMapper

class POICollector:
    """POI 数据采集器"""
    
    SEARCH_KEYWORDS = {
        'restaurants': [
            'restaurant',
            'cafe',
            'bakery',
            'fine dining',
            'local cuisine'
        ],
        'attractions': [
            'museum',
            'attraction',
            'landmark',
            'monument',
            'gallery',
            'theater'
        ],
        'hotels': [
            'hotel',
            'hostel',
            'resort',
            'accommodation'
        ]
    }
    
    GOOGLE_TYPES = {
        'restaurants': ['restaurant', 'cafe', 'bakery', 'bar'],
        'attractions': ['tourist_attraction', 'museum', 'park', 'art_gallery'],
        'hotels': ['lodging', 'hotel']
    }
    
    def __init__(self):
        print("="*80)
        print("🚀 Initializing POI Collector")
        print("="*80)
        
        self.db = Database()
        
        if not self.db.test_connection():
            raise Exception("Database connection failed")
        
        self.google_client = GooglePlacesClient()
        
        category_mappings = self.db.get_category_mappings()
        self.mapper = POIMapper(category_mappings)
        
        self.stats = {
            'total_found': 0,
            'new_inserted': 0,
            'existing_updated': 0,
            'failed': 0
        }
        
        print("✅ POI Collector initialized successfully")
        print("="*80 + "\n")
    
    def collect_city_pois(
        self,
        city_id: str,
        poi_type: str = 'all',
        limit: int = 0
    ) -> Dict[str, Any]:
        """采集指定城市的 POI 数据"""
        start_time = datetime.now()
        
        print("="*80)
        print(f"🚀 Starting POI collection")
        print(f"   City: {city_id}")
        print(f"   Type: {poi_type}")
        print(f"   Limit: {limit if limit > 0 else 'No limit'}")
        print("="*80 + "\n")
        
        city_config = self.db.get_city_config(city_id)
        if not city_config:
            error_msg = f"City '{city_id}' not found in database"
            print(f"❌ {error_msg}")
            return {'status': 'error', 'message': error_msg}
        
        print(f"📍 City: {city_config['city_name']} ({city_config['city_name_cn']})")
        print(f"   Location: ({city_config['latitude']}, {city_config['longitude']})")
        print(f"   Search radius: {city_config['search_radius']}m\n")
        
        types_to_collect = ['restaurants', 'attractions', 'hotels'] if poi_type == 'all' else [poi_type]
        
        for ptype in types_to_collect:
            print("\n" + "="*80)
            print(f"📦 Collecting {ptype}...")
            print("="*80 + "\n")
            
            try:
                self._collect_poi_type(
                    city_config=city_config,
                    poi_type=ptype,
                    limit=limit
                )
            except Exception as e:
                print(f"❌ Failed to collect {ptype}: {e}")
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("✅ Collection completed!")
        print("="*80)
        print("📊 Statistics:")
        print(f"   - Total found: {self.stats['total_found']}")
        print(f"   - New inserted: {self.stats['new_inserted']}")
        print(f"   - Existing updated: {self.stats['existing_updated']}")
        print(f"   - Failed: {self.stats['failed']}")
        print(f"   - API calls used: {self.google_client.api_calls_count}")
        print(f"   - Execution time: {execution_time:.2f}s")
        print("="*80 + "\n")
        
        return {
            'status': 'success',
            'stats': self.stats,
            'execution_time': execution_time
        }
    
    def _collect_poi_type(
        self,
        city_config: Dict[str, Any],
        poi_type: str,
        limit: int
    ) -> None:
        """采集特定类型的 POI"""
        location = (city_config['latitude'], city_config['longitude'])
        radius = city_config['search_radius']
        
        all_pois = []
        unique_place_ids = set()
        
        # 按关键词搜索
        keywords = self.SEARCH_KEYWORDS.get(poi_type, [])
        print(f"🔍 Searching with {len(keywords)} keywords...")
        
        for keyword in keywords:
            print(f"   Keyword: '{keyword}'")
            
            results = self.google_client.nearby_search(
                location=location,
                radius=radius,
                keyword=keyword
            )
            
            for poi in results:
                place_id = poi.get('place_id')
                if place_id and place_id not in unique_place_ids:
                    unique_place_ids.add(place_id)
                    all_pois.append(poi)
            
            time.sleep(0.5)
            
            if limit > 0 and len(all_pois) >= limit:
                print(f"   Reached limit of {limit} POIs")
                break
        
        # 按类型搜索
        if limit == 0 or len(all_pois) < limit:
            google_types = self.GOOGLE_TYPES.get(poi_type, [])
            print(f"\n🔍 Searching with {len(google_types)} Google types...")
            
            for gtype in google_types:
                if limit > 0 and len(all_pois) >= limit:
                    break
                
                print(f"   Type: '{gtype}'")
                
                results = self.google_client.nearby_search(
                    location=location,
                    radius=radius,
                    type=gtype
                )
                
                for poi in results:
                    place_id = poi.get('place_id')
                    if place_id and place_id not in unique_place_ids:
                        unique_place_ids.add(place_id)
                        all_pois.append(poi)
                
                time.sleep(0.5)
        
        if limit > 0:
            all_pois = all_pois[:limit]
        
        print(f"\n📦 Found {len(all_pois)} unique POIs")
        self.stats['total_found'] += len(all_pois)
        
        if all_pois:
            self._fetch_and_save_pois(
                pois=all_pois,
                city_id=city_config['city_id'],
                poi_type=poi_type
            )
    
    def _fetch_and_save_pois(
        self,
        pois: List[Dict[str, Any]],
        city_id: str,
        poi_type: str
    ) -> None:
        """获取 POI 详细信息并保存到数据库"""
        table_name = poi_type
        batch = []
        
        print(f"\n💾 Fetching details and saving to database...")
        
        for i, poi in enumerate(pois, 1):
            place_id = poi.get('place_id')
            poi_name = poi.get('name', 'Unknown')
            
            try:
                if i % 10 == 0 or i == len(pois):
                    print(f"   Progress: [{i}/{len(pois)}] {poi_name[:50]}")
                
                details = self.google_client.place_details(place_id)
                if not details:
                    print(f"   ⚠️  Failed to get details for {poi_name}")
                    self.stats['failed'] += 1
                    continue
                
                poi_data = self.mapper.transform_poi_data(
                    google_data=details,
                    city_id=city_id,
                    poi_type=poi_type
                )
                
                batch.append(poi_data)
                
                if len(batch) >= Config.BATCH_SIZE:
                    new_count, updated_count = self.db.bulk_insert_pois(table_name, batch)
                    self.stats['new_inserted'] += new_count
                    self.stats['existing_updated'] += updated_count
                    batch = []
                
            except Exception as e:
                print(f"   ❌ Error processing {poi_name}: {e}")
                self.stats['failed'] += 1
        
        if batch:
            new_count, updated_count = self.db.bulk_insert_pois(table_name, batch)
            self.stats['new_inserted'] += new_count
            self.stats['existing_updated'] += updated_count
        
        print(f"   ✅ Saved {self.stats['new_inserted']} new POIs")

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='TravelNest POI Data Collector',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--city-id', required=True, help='City ID to collect')
    parser.add_argument(
        '--poi-type',
        default='all',
        choices=['restaurants', 'attractions', 'hotels', 'all'],
        help='POI type to collect'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Maximum POIs to collect per type (0 = no limit)'
    )
    
    args = parser.parse_args()
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    try:
        collector = POICollector()
        result = collector.collect_city_pois(
            city_id=args.city_id,
            poi_type=args.poi_type,
            limit=args.limit
        )
        
        if result['status'] == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()