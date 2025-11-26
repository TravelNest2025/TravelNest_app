"""
POI数据爬取模块 - 支持分页获取更多结果 (Text Search 版本)

使用Google Places API (New) 的 Text Search 接口采集POI数据
并自动将经纬度转换为GIS格式 (POINT)
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
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
    """Google Places API爬虫 - 使用 Text Search 支持翻页"""
    
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
    
    def search_text_with_pagination(
        self,
        latitude: float,
        longitude: float,
        included_types: List[str],
        radius: int = 25000,
        max_results: int = 300,
    ) -> List[Dict]:
        """
        使用 Text Search 搜索 POI，支持真正的翻页获取更多结果
        
        Args:
            latitude: 中心纬度
            longitude: 中心经度
            included_types: 类型列表 (取第一个作为主要查询关键词)
            radius: 搜索半径（米）
            max_results: 期望的最大结果数
            
        Returns:
            POI列表
        """
        all_places = []
        next_page_token = None
        
        # 构造查询词：取列表第一个类型，例如 'restaurant'
        # 将下划线替换为空格，例如 'tourist_attraction' -> 'tourist attraction'
        primary_type = included_types[0] if included_types else 'point of interest'
        text_query = primary_type.replace('_', ' ')
        
        logger.info(f"🔍 开始 Text Search: 关键词='{text_query}', 目标数量={max_results}")
        
        while len(all_places) < max_results:
            current_count = len(all_places)
            logger.info(f"📄 正在获取下一页 (当前已获取: {current_count})...")
            
            # 调用单次搜索
            places, next_page_token = self._search_text_single(
                query=text_query,
                latitude=latitude,
                longitude=longitude,
                radius=radius,
                included_type=primary_type,
                page_token=next_page_token
            )
            
            if not places:
                logger.info("📄 本页无结果")
                break
            
            all_places.extend(places)
            logger.info(f"✅ 本页返回 {len(places)} 个结果，累计: {len(all_places)}")
            
            # 如果没有下一页令牌，说明Google没数据了
            if not next_page_token:
                logger.info("📄 API表示没有更多结果 (无 nextPageToken)")
                break
            
            # 如果已达到目标数量
            if len(all_places) >= max_results:
                break
            
            # ⏳ 关键：翻页之间必须有延迟，否则Google会报错或返回空
            logger.info("⏳ 等待 2 秒以获取下一页...")
            time.sleep(2)
        
        # 截断到精确的max_results
        result = all_places[:max_results]
        logger.info(f"🎯 搜索完成，共获取 {len(result)} 个结果")
        
        return result
    
    def _search_text_single(
        self,
        query: str,
        latitude: float,
        longitude: float,
        radius: int,
        included_type: str,
        page_token: str = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        单次 Text Search 调用
        """
        url = f'{self.base_url}:searchText'
        
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.google_config.api_key,
            # FieldMask: 只请求 Basic 字段以节省成本
            # 注意：必须包含 nextPageToken 才能翻页
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
                'places.nationalPhoneNumber,'
                'places.photos,'
                'nextPageToken' 
            )
        }
        
        payload = {
            'textQuery': query,
            # 使用 locationBias (圆形区域偏好)
            'locationBias': {
                'circle': {
                    'center': {
                        'latitude': latitude,
                        'longitude': longitude
                    },
                    'radius': radius
                }
            },
            # 严格过滤类型 (可选，如果结果太少可以注释掉这一行)
            'includedType': included_type,
            'languageCode': self.google_config.language,
            'regionCode': self.google_config.region,
        }
        
        # 如果有翻页令牌，加入 payload
        if page_token:
            payload['pageToken'] = page_token
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.api_calls += 1
            
            data = response.json()
            places = data.get('places', [])
            next_token = data.get('nextPageToken')
            
            return places, next_token
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Text Search 失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应内容: {e.response.text}")
            return [], None

    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """获取POI详细信息"""
        url = f'{self.base_url}/{place_id}'
        
        headers = {
            'X-Goog-Api-Key': self.google_config.api_key,
            'X-Goog-FieldMask': (
                'id,displayName,formattedAddress,location,rating,userRatingCount,'
                'priceLevel,types,websiteUri,nationalPhoneNumber,photos,editorialSummary'
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
        解析POI数据，并将经纬度转换为GIS格式
        """
        try:
            # 提取基础字段
            place_id = place_data.get('id', '')
            name = place_data.get('displayName', {}).get('text', '')
            
            # --- GIS 转换逻辑 ---
            location = place_data.get('location', {})
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            
            # 生成 PostGIS WKT 格式: POINT(lng lat)
            # 注意：GIS标准通常是先经度后纬度
            location_gis = None
            if latitude is not None and longitude is not None:
                location_gis = f"POINT({longitude} {latitude})"
            # -------------------
            
            address = place_data.get('formattedAddress', '')
            rating = place_data.get('rating')
            review_count = place_data.get('userRatingCount', 0)
            
            price_level_str = place_data.get('priceLevel', 'PRICE_LEVEL_UNSPECIFIED')
            price_level = self._parse_price_level(price_level_str)
            
            website = place_data.get('websiteUri', '')
            types = place_data.get('types', [])
            
            # 照片处理
            photos = place_data.get('photos', [])
            photo_references = [
                format_photo_reference({
                    'photo_reference': photo.get('name', '').split('/')[-1],
                    'width': photo.get('widthPx', 0),
                    'height': photo.get('heightPx', 0),
                    'html_attributions': photo.get('authorAttributions', []),
                })
                for photo in photos[:10]
            ]
            
            # 确定POI类型
            poi_type = determine_poi_type(types)
            
            # 类型映射
            if self.supabase_client:
                categories = map_types_to_categories_from_db(types, self.supabase_client)
            else:
                categories = []
            
            # 创建对象 (注意：这里假设你的 models 已经支持 location 字段)
            # 如果 models 还没改，location_gis 参数可能会报错，请确保 models.py 已更新
            
            common_args = {
                'city_id': city_config.city_id,
                'google_place_id': place_id,
                'name': name,
                'latitude': latitude,   # 保留原始字段以备不时之需
                'longitude': longitude, # 保留原始字段
                'location': location_gis, # ✅ 新增 GIS 字段
                'address': address,
                'website': website,
                'rating': rating,
                'review_count': review_count,
                'price_level': price_level,
                'price_source': 'google_attribute' if price_level is not None else 'unknown',
                'categories': categories,
                'photo_references': photo_references,
                'price_label': None,
            }

            if poi_type == 'restaurant':
                return Restaurant(
                    **common_args,
                    is_michelin=False,
                    currency='EUR',
                )
            
            elif poi_type == 'attraction':
                return Attraction(
                    **common_args,
                    is_free_entry=None,
                    ticket_status='unknown',
                    description=place_data.get('editorialSummary', {}).get('text', ''),
                )
            
            else:  # hotel
                return Hotel(
                    **common_args,
                    star_rating=None,
                    hotel_tier=None,
                    is_hostel=None,
                )
        
        except Exception as e:
            logger.error(f"❌ 解析place数据失败: {e}")
            logger.debug(f"数据: {place_data}")
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
    
    def crawl_city(self, city_id: str) -> CrawlResult:
        """爬取一个城市的所有POI"""
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
        爬取特定类型的POI（使用 Text Search 分页）
        """
        pois = []
        seen_place_ids = set()
        
        # 使用新的 Text Search 方法
        places = self.search_text_with_pagination(
            latitude=city_config.latitude,
            longitude=city_config.longitude,
            included_types=included_types,
            radius=city_config.search_radius,
            max_results=self.crawler_config.max_pois_per_type or 300,
        )
        
        logger.info(f"🔄 开始解析 {len(places)} 个原始结果...")
        
        for i, place_data in enumerate(places, 1):
            poi = self.parse_place(place_data, city_config)
            
            if poi and poi.google_place_id not in seen_place_ids:
                poi_type = determine_poi_type(place_data.get('types', []))
                
                # 宽松过滤：只要解析成功且ID不重复就保留
                # (Text Search 比较精准，通常不需要太严格的类型二次过滤，
                # 但为了保险起见，还是检查一下是否符合大类)
                if poi_type == expected_type:
                    pois.append(poi)
                    seen_place_ids.add(poi.google_place_id)
                else:
                    logger.debug(f"⏭️ 跳过类型不符: {poi.name} ({poi_type})")
            
            if self.crawler_config.max_pois_per_type and len(pois) >= self.crawler_config.max_pois_per_type:
                logger.info(f"🎯 已达到数量限制: {len(pois)}")
                break
        
        logger.info(f"✅ 解析完成，有效POI: {len(pois)} 个")
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
    output_file = sys.argv[2] if len(sys.argv) > 2 else f'./cache/{city_id}.json'
    
    # 初始化配置
    google_config = get_google_config()
    crawler_config = get_crawler_config()
    
    # 初始化Supabase客户端
    supabase_client = None
    try:
        supabase_config = get_supabase_config()
        print("DEBUG: 正在尝试连接 Supabase...")
        print(f"DEBUG: URL={supabase_config.url}, KEY长度={len(str(supabase_config.key))}")
        supabase_client = create_client(supabase_config.url, supabase_config.key)
        logger.info("✅ Supabase客户端初始化成功（用于读取映射规则）")
    except Exception as e:
        logger.warning(f"⚠️  Supabase客户端初始化失败，将使用硬编码映射: {e}")
    
    # 创建爬虫
    crawler = GooglePlacesCrawler(google_config, crawler_config, supabase_client)
    
    # 执行爬取
    try:
        result = crawler.crawl_city(city_id)
        
        # 保存结果
        import os
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
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
        logger.error(f"❌ 爬取失败: {e}", exc_info=True)
        sys.exit(1)