"""
POI数据爬取模块

使用Google Places API (New) 采集POI数据
"""

import requests
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

from models import Restaurant, Attraction, Hotel, CrawlResult, format_photo_reference
from config import GooglePlacesConfig, CityConfig, CrawlerConfig, get_city_config
from type_mapping import (
    determine_poi_type,
    map_types_to_categories_from_db,
    get_auxiliary_tags_from_db,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GooglePlacesCrawler:
    """Google Places API爬虫"""
    
    def __init__(
        self,
        google_config: GooglePlacesConfig,
        crawler_config: CrawlerConfig,
        supabase_client = None,
    ):
        self.google_config = google_config
        self.crawler_config = crawler_config
        self.supabase_client = supabase_client
        self.api_calls = 0
        
        # Google Places API (New) 基础URL
        self.base_url = 'https://places.googleapis.com/v1/places'
    
    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        included_types: List[str],
        radius: int = 25000,
        max_results: int = 60,
    ) -> List[Dict]:
        """
        使用Nearby Search搜索附近的POI
        
        Args:
            latitude: 纬度
            longitude: 经度
            included_types: 包含的类型列表
            radius: 搜索半径（米）
            max_results: 最大结果数
            
        Returns:
            POI列表
        """
        url = f'{self.base_url}:searchNearby'
        
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.google_config.api_key,
            'X-Goog-FieldMask': (
                'places.id,'
                'places.displayName,'
                'places.formattedAddress,'
                'places.location,'
                'places.rating,'
                'places.userRatingCount,'
                'places.priceLevel,'
                'places.types,'
                'places.websiteUri,'
                'places.photos'
            )
        }
        
        payload = {
            'includedTypes': included_types,
            'maxResultCount': min(max_results, 20),  # API限制单次最多20个
            'locationRestriction': {
                'circle': {
                    'center': {
                        'latitude': latitude,
                        'longitude': longitude
                    },
                    'radius': radius
                }
            },
            'languageCode': self.google_config.language,
            'regionCode': self.google_config.region,
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.api_calls += 1
            
            data = response.json()
            places = data.get('places', [])
            
            logger.info(f"✅ Nearby Search返回 {len(places)} 个结果")
            
            return places
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Nearby Search失败: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"响应内容: {e.response.text}")
            return []
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        获取POI详细信息（如果Nearby Search字段不够）
        
        Args:
            place_id: Place ID
            
        Returns:
            详细信息字典
        """
        url = f'{self.base_url}/{place_id}'
        
        headers = {
            'X-Goog-Api-Key': self.google_config.api_key,
            'X-Goog-FieldMask': (
                'id,'
                'displayName,'
                'formattedAddress,'
                'location,'
                'rating,'
                'userRatingCount,'
                'priceLevel,'
                'types,'
                'websiteUri,'
                'photos,'
                'editorialSummary'  # 描述
            )
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            self.api_calls += 1
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 获取Place Details失败: {e}")
            return None
    
    def parse_place(self, place_data: Dict, city_config: CityConfig) -> Optional[Restaurant | Attraction | Hotel]:
        """
        解析Google Places返回的POI数据
        
        Args:
            place_data: Google Places API返回的place数据
            city_config: 城市配置
            
        Returns:
            POI对象（Restaurant/Attraction/Hotel）
        """
        try:
            # 提取基础字段
            place_id = place_data.get('id', '')
            name = place_data.get('displayName', {}).get('text', '')
            location = place_data.get('location', {})
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            address = place_data.get('formattedAddress', '')
            rating = place_data.get('rating')
            review_count = place_data.get('userRatingCount', 0)
            
            # 价格等级（Google使用PRICE_LEVEL_UNSPECIFIED=0到PRICE_LEVEL_VERY_EXPENSIVE=4）
            price_level_str = place_data.get('priceLevel', 'PRICE_LEVEL_UNSPECIFIED')
            price_level = self._parse_price_level(price_level_str)
            
            website = place_data.get('websiteUri', '')
            types = place_data.get('types', [])
            
            # 照片处理（仅存储photo_reference）
            photos = place_data.get('photos', [])
            photo_references = [
                format_photo_reference({
                    'photo_reference': photo.get('name', '').split('/')[-1],  # 提取reference
                    'width': photo.get('widthPx', 0),
                    'height': photo.get('heightPx', 0),
                    'html_attributions': photo.get('authorAttributions', []),
                })
                for photo in photos[:10]  # 最多保存10张照片引用
            ]
            
            # 确定POI类型
            poi_type = determine_poi_type(types)
            
            # 应用类型映射 - 从数据库读取
            if self.supabase_client:
                categories = map_types_to_categories_from_db(types, self.supabase_client)
                # 获取辅助标签（romantic, family）用于后续AI参考
                auxiliary_tags = get_auxiliary_tags_from_db(types, self.supabase_client)
                logger.debug(f"辅助标签建议: {auxiliary_tags}")
            else:
                # 无Supabase客户端，categories为空
                logger.error("❌ 未提供Supabase客户端，无法查询类型映射")
                categories = []
            
            # 根据POI类型创建相应对象
            # Phase 1不做特殊判断，所有特殊字段留给Phase 2 AI处理
            if poi_type == 'restaurant':
                return Restaurant(
                    city_id=city_config.city_id,
                    google_place_id=place_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    website=website,
                    rating=rating,
                    review_count=review_count,
                    price_level=price_level,
                    price_label=None,  # Phase 2 AI处理
                    price_source='google_attribute' if price_level is not None else 'unknown',
                    categories=categories,
                    photo_references=photo_references,
                    is_michelin=False,  # Phase 2 AI处理
                    currency='EUR',
                )
            
            elif poi_type == 'attraction':
                return Attraction(
                    city_id=city_config.city_id,
                    google_place_id=place_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    website=website,
                    rating=rating,
                    review_count=review_count,
                    price_level=price_level,
                    price_label=None,  # Phase 2 AI处理
                    price_source='google_attribute' if price_level is not None else 'unknown',
                    categories=categories,
                    photo_references=photo_references,
                    is_free_entry=None,  # Phase 2 AI处理
                    ticket_status='unknown',  # Phase 2 AI处理
                    description=place_data.get('editorialSummary', {}).get('text', ''),
                )
            
            else:  # hotel
                return Hotel(
                    city_id=city_config.city_id,
                    google_place_id=place_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    website=website,
                    rating=rating,
                    review_count=review_count,
                    price_level=price_level,
                    price_label=None,  # Phase 2 AI处理
                    price_source='google_attribute' if price_level is not None else 'unknown',
                    categories=categories,
                    photo_references=photo_references,
                    star_rating=None,  # Phase 2 AI处理
                    hotel_tier=None,  # Phase 2 AI处理
                    is_hostel=None,  # Phase 2 AI处理
                )
        
        except Exception as e:
            logger.error(f"❌ 解析place数据失败: {e}")
            logger.error(f"数据: {place_data}")
            return None
    
    def _parse_price_level(self, price_level_str: str) -> Optional[int]:
        """解析Google的价格等级字符串"""
        price_map = {
            'PRICE_LEVEL_UNSPECIFIED': None,
            'PRICE_LEVEL_FREE': 0,
            'PRICE_LEVEL_INEXPENSIVE': 1,
            'PRICE_LEVEL_MODERATE': 2,
            'PRICE_LEVEL_EXPENSIVE': 3,
            'PRICE_LEVEL_VERY_EXPENSIVE': 4,
        }
        return price_map.get(price_level_str)
    
    def _estimate_star_rating(self, place_data: Dict, types: List[str]) -> Optional[int]:
        """估算酒店星级（Google不直接提供）"""
        # 基于类型和评分估算
        rating = place_data.get('rating', 0)
        
        # 如果types中包含具体星级信息（某些地区Google会提供）
        for t in types:
            if '5_star' in t or 'luxury' in t:
                return 5
            elif '4_star' in t or 'upscale' in t:
                return 4
            elif '3_star' in t:
                return 3
            elif '2_star' in t or 'budget' in t:
                return 2
            elif '1_star' in t:
                return 1
        
        # 基于评分估算（粗略）
        if rating >= 4.5:
            return 5
        elif rating >= 4.0:
            return 4
        elif rating >= 3.5:
            return 3
        elif rating >= 3.0:
            return 2
        elif rating > 0:
            return 1
        
        return None
    
    def crawl_city(self, city_id: str) -> CrawlResult:
        """
        爬取一个城市的所有POI
        
        Args:
            city_id: 城市ID
            
        Returns:
            爬取结果
        """
        logger.info(f"🚀 开始爬取城市: {city_id}")
        
        city_config = get_city_config(city_id)
        result = CrawlResult(city_id=city_id)
        result.crawl_time = datetime.now()
        
        # 1. 爬取餐厅
        if self.crawler_config.crawl_restaurants:
            logger.info("📍 爬取餐厅...")
            restaurants = self._crawl_type(
                city_config,
                ['restaurant', 'cafe', 'bakery', 'bar'],
                'restaurant'
            )
            result.restaurants = restaurants
            logger.info(f"✅ 爬取到 {len(restaurants)} 个餐厅")
        
        # 2. 爬取景点
        if self.crawler_config.crawl_attractions:
            logger.info("📍 爬取景点...")
            attractions = self._crawl_type(
                city_config,
                ['tourist_attraction', 'museum', 'art_gallery', 'park'],
                'attraction'
            )
            result.attractions = attractions
            logger.info(f"✅ 爬取到 {len(attractions)} 个景点")
        
        # 3. 爬取酒店
        if self.crawler_config.crawl_hotels:
            logger.info("📍 爬取酒店...")
            hotels = self._crawl_type(
                city_config,
                ['lodging', 'hotel'],
                'hotel'
            )
            result.hotels = hotels
            logger.info(f"✅ 爬取到 {len(hotels)} 个酒店")
        
        result.total_pois = len(result.restaurants) + len(result.attractions) + len(result.hotels)
        result.api_calls = self.api_calls
        
        logger.info(f"🎉 爬取完成！总计: {result.total_pois} 个POI，API调用: {self.api_calls} 次")
        
        return result
    
    def _crawl_type(
        self,
        city_config: CityConfig,
        included_types: List[str],
        expected_type: str
    ) -> List[Restaurant | Attraction | Hotel]:
        """
        爬取特定类型的POI
        
        Args:
            city_config: 城市配置
            included_types: Google Places类型列表
            expected_type: 期望的POI类型（用于过滤）
            
        Returns:
            POI列表
        """
        pois = []
        seen_place_ids = set()
        
        # 调用Nearby Search
        places = self.search_nearby(
            latitude=city_config.latitude,
            longitude=city_config.longitude,
            included_types=included_types,
            radius=city_config.search_radius,
            max_results=self.crawler_config.max_pois_per_type or 60,
        )
        
        # 解析每个place
        for place_data in places:
            # 请求延迟（避免触发限流）
            time.sleep(self.crawler_config.request_delay)
            
            poi = self.parse_place(place_data, city_config)
            
            if poi and poi.google_place_id not in seen_place_ids:
                # 验证POI类型是否符合预期
                poi_type = determine_poi_type(place_data.get('types', []))
                if poi_type == expected_type:
                    pois.append(poi)
                    seen_place_ids.add(poi.google_place_id)
            
            # 检查是否达到限制
            if self.crawler_config.max_pois_per_type and len(pois) >= self.crawler_config.max_pois_per_type:
                break
        
        return pois


# ==========================================
# 命令行入口
# ==========================================

if __name__ == '__main__':
    import sys
    import json
    from config import get_google_config, get_crawler_config, get_supabase_config
    from supabase import create_client
    
    # 解析命令行参数
    city_id = sys.argv[1] if len(sys.argv) > 1 else 'paris'
    output_file = sys.argv[2] if len(sys.argv) > 2 else f'./cache/{city_id}_crawl_result.json'
    
    # 初始化配置
    google_config = get_google_config()
    crawler_config = get_crawler_config()
    
    # 初始化Supabase客户端（用于读取映射表）
    supabase_client = None
    try:
        supabase_config = get_supabase_config()
        supabase_client = create_client(supabase_config.url, supabase_config.key)
        logger.info("✅ Supabase客户端初始化成功（用于读取映射规则）")
    except Exception as e:
        logger.warning(f"⚠️  Supabase客户端初始化失败，将使用硬编码映射: {e}")
    
    # 创建爬虫（传入supabase_client）
    crawler = GooglePlacesCrawler(google_config, crawler_config, supabase_client)
    
    # 执行爬取
    try:
        result = crawler.crawl_city(city_id)
        
        # 保存结果
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        result.save_to_file(output_file)
        
        logger.info(f"✅ 结果已保存到: {output_file}")
        
        # 打印统计信息
        print("\n=== 爬取统计 ===")
        print(f"城市: {city_id}")
        print(f"餐厅: {len(result.restaurants)}")
        print(f"景点: {len(result.attractions)}")
        print(f"酒店: {len(result.hotels)}")
        print(f"总计: {result.total_pois}")
        print(f"API调用: {result.api_calls}")
        
    except Exception as e:
        logger.error(f"❌ 爬取失败: {e}")
        sys.exit(1)