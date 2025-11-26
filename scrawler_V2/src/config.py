"""
配置管理模块

管理环境变量、API密钥、数据库连接等配置
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


@dataclass
class GooglePlacesConfig:
    """Google Places API配置"""
    
    api_key: str
    language: str = 'zh-CN'
    region: str = 'fr'  # 法国
    
    # API限制
    max_results_per_query: int = 60  # Google Places API单次最多返回60个结果
    radius: int = 25000  # 搜索半径（米）
    
    @classmethod
    def from_env(cls) -> 'GooglePlacesConfig':
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            raise ValueError('GOOGLE_PLACES_API_KEY环境变量未设置')
        
        return cls(
            api_key=api_key,
            language=os.getenv('GOOGLE_LANGUAGE', 'zh-CN'),
            region=os.getenv('GOOGLE_REGION', 'fr'),
        )


@dataclass
class SupabaseConfig:
    """Supabase配置"""
    
    url: str
    key: str
    schema: str = 'public'
    
    @classmethod
    def from_env(cls) -> 'SupabaseConfig':
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError('SUPABASE_URL和SUPABASE_KEY环境变量未设置')
        
        return cls(
            url=url,
            key=key,
            schema=os.getenv('SUPABASE_SCHEMA', 'public'),
        )


@dataclass
class CityConfig:
    """城市配置"""
    
    city_id: str
    city_name: str
    city_name_cn: str
    country: str
    country_code: str
    region: str
    
    # 地理中心点
    latitude: float
    longitude: float
    search_radius: int = 25000  # 米
    
    # 优先级
    priority: str = 'high'
    
    # 分类（指导采集重点）
    categories: list[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []


# ==========================================
# 预定义城市配置
# ==========================================

CITIES = {
    'paris': CityConfig(
        city_id='paris',
        city_name='Paris',
        city_name_cn='巴黎',
        country='France',
        country_code='FR',
        region='Western Europe',
        latitude=48.8566,
        longitude=2.3522,
        search_radius=25000,
        priority='high',
        categories=[
            'museums',
            'historical_landmarks',
            'art_galleries',
            'romantic_spots',
            'michelin_restaurants',
            'shopping_districts',
            'parks',
        ]
    ),
}


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    
    # 目标城市
    target_cities: list[str]
    
    # POI类型
    crawl_restaurants: bool = True
    crawl_attractions: bool = True
    crawl_hotels: bool = True
    
    # 限制
    max_pois_per_type: Optional[int] = None  # None表示不限制
    
    # 缓存
    cache_dir: str = './cache'
    cache_enabled: bool = True
    
    # 重试
    max_retries: int = 3
    retry_delay: int = 5  # 秒
    
    # 请求间隔（避免触发API限流）
    request_delay: float = 0.1  # 秒
    
    @classmethod
    def from_env(cls) -> 'CrawlerConfig':
        return cls(
            target_cities=os.getenv('TARGET_CITIES', 'paris').split(','),
            crawl_restaurants=os.getenv('CRAWL_RESTAURANTS', 'true').lower() == 'true',
            crawl_attractions=os.getenv('CRAWL_ATTRACTIONS', 'true').lower() == 'true',
            crawl_hotels=os.getenv('CRAWL_HOTELS', 'true').lower() == 'true',
            max_pois_per_type=int(os.getenv('MAX_POIS_PER_TYPE')) if os.getenv('MAX_POIS_PER_TYPE') else None,
            cache_dir=os.getenv('CACHE_DIR', './cache'),
        )


@dataclass
class WriterConfig:
    """写入器配置"""
    
    # 批量写入大小
    batch_size: int = 50
    
    # 去重策略
    skip_existing: bool = True  # 跳过已存在的记录（基于google_place_id）
    update_existing: bool = False  # 是否更新已存在的记录
    
    # 重试
    max_retries: int = 3
    retry_delay: int = 5
    
    @classmethod
    def from_env(cls) -> 'WriterConfig':
        return cls(
            batch_size=int(os.getenv('BATCH_SIZE', '50')),
            skip_existing=os.getenv('SKIP_EXISTING', 'true').lower() == 'true',
            update_existing=os.getenv('UPDATE_EXISTING', 'false').lower() == 'true',
        )


# ==========================================
# 全局配置实例
# ==========================================

def get_google_config() -> GooglePlacesConfig:
    """获取Google Places配置"""
    return GooglePlacesConfig.from_env()


def get_supabase_config() -> SupabaseConfig:
    """获取Supabase配置"""
    return SupabaseConfig.from_env()


def get_crawler_config() -> CrawlerConfig:
    """获取爬虫配置"""
    return CrawlerConfig.from_env()


def get_writer_config() -> WriterConfig:
    """获取写入器配置"""
    return WriterConfig.from_env()


def get_city_config(city_id: str) -> CityConfig:
    """获取城市配置"""
    if city_id not in CITIES:
        raise ValueError(f'城市 {city_id} 不存在于配置中')
    return CITIES[city_id]


# ==========================================
# 环境变量验证
# ==========================================

def validate_env() -> dict[str, bool]:
    """
    验证必需的环境变量是否已设置
    
    Returns:
        验证结果字典
    """
    results = {}
    
    # 必需的环境变量
    required_vars = [
        'GOOGLE_MAPS_API_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY',
    ]
    
    for var in required_vars:
        results[var] = bool(os.getenv(var))
    
    # 可选的环境变量
    optional_vars = [
        'TARGET_CITIES',
        'CACHE_DIR',
        'BATCH_SIZE',
    ]
    
    for var in optional_vars:
        results[f'{var} (optional)'] = bool(os.getenv(var))
    
    return results


def print_env_status():
    """打印环境变量状态"""
    print("=== 环境变量验证 ===")
    results = validate_env()
    
    all_required_set = True
    for var, is_set in results.items():
        if '(optional)' in var:
            status = '✅' if is_set else '⚠️ '
        else:
            status = '✅' if is_set else '❌'
            if not is_set:
                all_required_set = False
        
        print(f"{status} {var}: {'已设置' if is_set else '未设置'}")
    
    print()
    if all_required_set:
        print("✅ 所有必需的环境变量已设置")
    else:
        print("❌ 部分必需的环境变量未设置")
        print("请检查.env文件或GitHub Secrets配置")
    
    return all_required_set


# ==========================================
# 测试
# ==========================================

if __name__ == '__main__':
    print_env_status()
    
    print("\n=== 城市配置测试 ===")
    paris = get_city_config('paris')
    print(f"城市: {paris.city_name_cn} ({paris.city_name})")
    print(f"坐标: ({paris.latitude}, {paris.longitude})")
    print(f"搜索半径: {paris.search_radius}m")
    print(f"分类: {', '.join(paris.categories)}")