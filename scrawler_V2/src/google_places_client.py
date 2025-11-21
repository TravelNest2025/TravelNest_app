"""
Google Places API 客户端
"""
import googlemaps
import time
from typing import List, Dict, Any, Optional

from .config import Config

class GooglePlacesClient:
    """Google Places API 客户端"""
    
    def __init__(self):
        try:
            self.client = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
            self.api_calls_count = 0
            print("✅ Google Maps client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Google Maps client: {e}")
            raise
    
    def nearby_search(
        self,
        location: tuple,
        radius: int,
        keyword: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """附近搜索 POIs"""
        all_results = []
        
        try:
            search_params = {
                'location': location,
                'radius': radius
            }
            
            if keyword:
                search_params['keyword'] = keyword
            if type:
                search_params['type'] = type
            
            # 第一页
            response = self.client.places_nearby(**search_params)
            self.api_calls_count += 1
            all_results.extend(response.get('results', []))
            
            # 处理分页
            next_page_token = response.get('next_page_token')
            pages = 1
            
            while next_page_token and pages < 3:
                time.sleep(2)
                
                try:
                    response = self.client.places_nearby(page_token=next_page_token)
                    self.api_calls_count += 1
                    
                    new_results = response.get('results', [])
                    all_results.extend(new_results)
                    pages += 1
                    
                    next_page_token = response.get('next_page_token')
                except Exception as e:
                    print(f"   ⚠️  Failed to fetch page {pages + 1}: {e}")
                    break
            
            return all_results
        
        except Exception as e:
            print(f"   ❌ Nearby search failed: {e}")
            return []
    
    def place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """获取 POI 详细信息"""
        try:
            response = self.client.place(
                place_id=place_id,
                fields=[
                    'place_id',
                    'name',
                    'formatted_address',
                    'geometry',
                    'types',
                    'rating',
                    'user_ratings_total',
                    'price_level',
                    'opening_hours',
                    'formatted_phone_number',
                    'international_phone_number',
                    'website',
                    'photos'
                ]
            )
            
            self.api_calls_count += 1
            time.sleep(Config.REQUEST_DELAY)
            
            return response.get('result')
        
        except Exception as e:
            print(f"   ❌ Place details failed for {place_id}: {e}")
            return None