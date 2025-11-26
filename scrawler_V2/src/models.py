"""
数据模型定义

对应数据库schema的Python数据类
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import json


@dataclass
class POIBase:
    """POI基础数据模型"""
    
    # 基础信息
    city_id: str
    google_place_id: str
    name: str
    name_cn: Optional[str] = None
    
    # 地理位置
    latitude: float = None
    longitude: float = None
    address: Optional[str] = None
    website: Optional[str] = None
    
    # 评分和评论
    rating: Optional[float] = None
    review_count: Optional[int] = None
    
    # 价格信息
    price_level: Optional[int] = None
    price_label: Optional[str] = None
    price_source: str = 'google_attribute'
    
    # 分类
    categories: List[str] = field(default_factory=list)
    
    # 照片（存储photo_reference而非URL）
    photo_references: List[dict] = field(default_factory=list)
    
    # 状态
    is_active: bool = True
    enrichment_status: str = 'pending'
    
    # 时间戳
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        data = asdict(self)
        
        # 处理datetime
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        
        return data
    
    def to_db_dict(self) -> dict:
        """转换为数据库格式"""
        return {
            'city_id': self.city_id,
            'google_place_id': self.google_place_id,
            'name': self.name,
            'name_cn': self.name_cn,
            'location': f'SRID=4326;POINT({self.longitude} {self.latitude})' if self.longitude and self.latitude else None,
            'address': self.address,
            'website': self.website,
            'rating': self.rating,
            'review_count': self.review_count,
            'price_level': self.price_level,
            'price_label': self.price_label,
            'price_source': self.price_source,
            'categories': self.categories,
            'images_data': json.dumps(self.photo_references) if self.photo_references else None,
            'is_active': self.is_active,
            'enrichment_status': self.enrichment_status,
            'last_updated': datetime.utcnow().isoformat(),
        }


@dataclass
class Restaurant(POIBase):
    """餐厅数据模型"""
    
    # 餐厅特有字段
    is_michelin: bool = False
    michelin_stars: Optional[int] = None
    currency: str = 'EUR'
    
    def to_db_dict(self) -> dict:
        """转换为数据库格式"""
        data = super().to_db_dict()
        data.update({
            'is_michelin': self.is_michelin,
            'michelin_stars': self.michelin_stars,
            'currency': self.currency,
        })
        return data


@dataclass
class Attraction(POIBase):
    """景点数据模型"""
    
    # 景点特有字段
    is_free_entry: Optional[bool] = None
    standard_adult_price: Optional[float] = None
    ticket_status: str = 'unknown'
    description: Optional[str] = None
    visit_duration: Optional[int] = None  # 分钟
    best_time_to_visit: Optional[str] = None
    
    def to_db_dict(self) -> dict:
        """转换为数据库格式"""
        data = super().to_db_dict()
        data.update({
            'is_free_entry': self.is_free_entry,
            'standard_adult_price': self.standard_adult_price,
            'ticket_status': self.ticket_status,
            'description': self.description,
            'visit_duration': self.visit_duration,
            'best_time_to_visit': self.best_time_to_visit,
        })
        
        # 景点价格来源默认为rule_based
        if not data.get('price_source'):
            data['price_source'] = 'rule_based'
        
        return data


@dataclass
class Hotel(POIBase):
    """酒店数据模型"""
    
    # 酒店特有字段
    star_rating: Optional[int] = None
    hotel_tier: Optional[str] = None
    is_hostel: bool = False
    
    def to_db_dict(self) -> dict:
        """转换为数据库格式"""
        data = super().to_db_dict()
        data.update({
            'star_rating': self.star_rating,
            'hotel_tier': self.hotel_tier,
            'is_hostel': self.is_hostel,
        })
        
        # 酒店价格来源默认为google_stars
        if not data.get('price_source'):
            data['price_source'] = 'google_stars'
        
        return data


@dataclass
class CrawlResult:
    """爬取结果汇总"""
    
    city_id: str
    total_pois: int = 0
    restaurants: List[Restaurant] = field(default_factory=list)
    attractions: List[Attraction] = field(default_factory=list)
    hotels: List[Hotel] = field(default_factory=list)
    
    # 统计信息
    api_calls: int = 0
    errors: List[dict] = field(default_factory=list)
    crawl_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            'city_id': self.city_id,
            'total_pois': self.total_pois,
            'restaurants': [r.to_dict() for r in self.restaurants],
            'attractions': [a.to_dict() for a in self.attractions],
            'hotels': [h.to_dict() for h in self.hotels],
            'api_calls': self.api_calls,
            'errors': self.errors,
            'crawl_time': self.crawl_time.isoformat() if self.crawl_time else None,
            'statistics': {
                'restaurant_count': len(self.restaurants),
                'attraction_count': len(self.attractions),
                'hotel_count': len(self.hotels),
            }
        }
    
    def save_to_file(self, filepath: str):
        """保存到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'CrawlResult':
        """从JSON文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = cls(city_id=data['city_id'])
        result.total_pois = data['total_pois']
        result.api_calls = data['api_calls']
        result.errors = data['errors']
        
        if data.get('crawl_time'):
            result.crawl_time = datetime.fromisoformat(data['crawl_time'])
        
        # 重建POI对象
        for r_data in data['restaurants']:
            result.restaurants.append(Restaurant(**{
                k: v for k, v in r_data.items() 
                if k not in ['created_at', 'last_updated']
            }))
        
        for a_data in data['attractions']:
            result.attractions.append(Attraction(**{
                k: v for k, v in a_data.items() 
                if k not in ['created_at', 'last_updated']
            }))
        
        for h_data in data['hotels']:
            result.hotels.append(Hotel(**{
                k: v for k, v in h_data.items() 
                if k not in ['created_at', 'last_updated']
            }))
        
        return result


@dataclass
class WriteResult:
    """写入结果"""
    
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0  # 已存在的记录
    errors: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'errors': self.errors,
        }


# ==========================================
# 照片引用处理
# ==========================================

def format_photo_reference(photo_data: dict) -> dict:
    """
    格式化Google Photos返回的photo数据
    
    Google返回格式:
    {
        "photo_reference": "xxxx",
        "height": 800,
        "width": 1200,
        "html_attributions": ["<a href=...>"]
    }
    
    我们存储格式:
    {
        "reference": "xxxx",
        "width": 1200,
        "height": 800,
        "attribution": "..."
    }
    
    Args:
        photo_data: Google Photos API返回的数据
        
    Returns:
        格式化后的字典
    """
    return {
        'reference': photo_data.get('photo_reference', ''),
        'width': photo_data.get('width', 0),
        'height': photo_data.get('height', 0),
        'attribution': photo_data.get('html_attributions', [''])[0] if photo_data.get('html_attributions') else '',
    }


def build_photo_url(photo_reference: str, max_width: int = 800, api_key: str = '') -> str:
    """
    根据photo_reference构建Google Places Photo URL
    
    前端使用示例：
    const photoUrl = buildPhotoUrl(poi.images_data[0].reference, 800, GOOGLE_API_KEY)
    
    Args:
        photo_reference: 照片引用ID
        max_width: 图片最大宽度
        api_key: Google API Key
        
    Returns:
        完整的照片URL
    """
    base_url = 'https://maps.googleapis.com/maps/api/place/photo'
    return f'{base_url}?maxwidth={max_width}&photo_reference={photo_reference}&key={api_key}'


# ==========================================
# 测试
# ==========================================

if __name__ == '__main__':
    # 测试Restaurant模型
    restaurant = Restaurant(
        city_id='paris',
        google_place_id='ChIJxxx',
        name='Le Jules Verne',
        latitude=48.8584,
        longitude=2.2945,
        rating=4.5,
        review_count=1200,
        price_level=4,
        price_label='Luxury',
        is_michelin=True,
        michelin_stars=1,
        categories=['food'],
        photo_references=[
            {'reference': 'xxx123', 'width': 1200, 'height': 800, 'attribution': 'Google'}
        ]
    )
    
    print("=== Restaurant Model Test ===")
    print(json.dumps(restaurant.to_dict(), indent=2, ensure_ascii=False))
    
    # 测试序列化和反序列化
    print("\n=== CrawlResult Serialization Test ===")
    result = CrawlResult(city_id='paris')
    result.restaurants.append(restaurant)
    result.total_pois = 1
    result.api_calls = 5
    result.crawl_time = datetime.now()
    
    # 保存和加载
    test_file = '/tmp/test_crawl_result.json'
    result.save_to_file(test_file)
    print(f"✅ Saved to {test_file}")
    
    loaded_result = CrawlResult.load_from_file(test_file)
    print(f"✅ Loaded: {loaded_result.total_pois} POIs, {len(loaded_result.restaurants)} restaurants")
    
    print("\n=== All Tests Passed ===")