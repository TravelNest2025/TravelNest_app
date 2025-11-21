"""
POI 分类映射模块
"""
from typing import List, Dict, Any, Optional

from .config import Config

class POIMapper:
    """POI 分类映射器"""
    
    def __init__(self, category_mappings: Dict[str, Dict[str, Any]]):
        self.mappings = category_mappings
        print(f"✅ POIMapper initialized with {len(category_mappings)} mappings")
    
    def map_categories(self, google_types: List[str]) -> List[str]:
        """从 Google types 映射到我们的 categories"""
        if not google_types:
            return []
        
        category_scores = {}
        
        for gtype in google_types:
            if gtype in self.mappings:
                mapping = self.mappings[gtype]
                categories = mapping['categories']
                confidence = mapping['confidence']
                
                for cat in categories:
                    if cat not in category_scores:
                        category_scores[cat] = 0
                    category_scores[cat] = max(category_scores[cat], confidence)
        
        if not category_scores:
            return []
        
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [cat for cat, score in sorted_categories]
    
    def calculate_enrichment_priority(
        self,
        rating: Optional[float],
        review_count: Optional[int]
    ) -> int:
        """计算 POI 的 AI 增强优先级"""
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
    
    def transform_poi_data(
        self,
        google_data: Dict[str, Any],
        city_id: str,
        poi_type: str
    ) -> Dict[str, Any]:
        """将 Google Places API 数据转换为数据库格式"""
        geometry = google_data.get('geometry', {})
        location = geometry.get('location', {})
        
        google_types = google_data.get('types', [])
        categories = self.map_categories(google_types)
        
        poi_data = {
            'city_id': city_id,
            'google_place_id': google_data.get('place_id'),
            'name': google_data.get('name'),
            'location': f"POINT({location.get('lng')} {location.get('lat')})",
            'address': google_data.get('formatted_address'),
            'phone': google_data.get('formatted_phone_number') or google_data.get('international_phone_number'),
            'website': google_data.get('website'),
            'rating': google_data.get('rating'),
            'review_count': google_data.get('user_ratings_total'),
            'price_level': google_data.get('price_level'),
            'google_types': google_types,
            'categories': categories if categories else None,
            'opening_hours': self._extract_opening_hours(google_data),
            'photo_urls': self._extract_photo_urls(google_data),
            'primary_photo_url': self._get_primary_photo_url(google_data),
            'data_enrichment_level': 'basic',
            'category_source': 'google_types',
            'enrichment_priority': self.calculate_enrichment_priority(
                google_data.get('rating'),
                google_data.get('user_ratings_total')
            )
        }
        
        return poi_data
    
    def _extract_opening_hours(self, google_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取营业时间"""
        opening_hours = google_data.get('opening_hours')
        if not opening_hours:
            return None
        
        return {
            'open_now': opening_hours.get('open_now'),
            'weekday_text': opening_hours.get('weekday_text', [])
        }
    
    def _extract_photo_urls(self, google_data: Dict[str, Any]) -> Optional[List[str]]:
        """提取照片 URLs"""
        photos = google_data.get('photos', [])
        if not photos:
            return None
        
        photo_urls = []
        for photo in photos[:5]:
            photo_ref = photo.get('photo_reference')
            if photo_ref:
                url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={Config.GOOGLE_MAPS_API_KEY}"
                photo_urls.append(url)
        
        return photo_urls if photo_urls else None
    
    def _get_primary_photo_url(self, google_data: Dict[str, Any]) -> Optional[str]:
        """获取主照片 URL"""
        photos = google_data.get('photos', [])
        if not photos:
            return None
        
        photo_ref = photos[0].get('photo_reference')
        if photo_ref:
            return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={Config.GOOGLE_MAPS_API_KEY}"
        
        return None