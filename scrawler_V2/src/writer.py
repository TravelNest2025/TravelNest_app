"""
简化的重试写入脚本 - 独立版本，不依赖其他文件

使用场景：
1. 爬取成功但写入失败 → 从缓存重试
2. GitHub Actions中写入失败 → 下载Artifacts后重试

命令示例：
python src/retry_writer.py --cache-file ./cache/paris.json
"""

import argparse
import json
import logging
import sys
import os
import time
from pathlib import Path
from typing import Dict

from supabase import create_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetryWriter:
    """重试写入器"""
    
    def __init__(self, supabase_url, supabase_key):
        self.supabase = create_client(supabase_url, supabase_key)
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def write_single_poi(self, poi_data: Dict, poi_type: str, max_retries=3) -> bool:
        """
        写入单个POI，带重试机制
        
        Args:
            poi_data: POI数据字典
            poi_type: 'restaurant' | 'attraction' | 'hotel'
            max_retries: 最大重试次数
            
        Returns:
            True if success, False if failed
        """
        table_name = f"{poi_type}s"  # restaurants, attractions, hotels
        
        for attempt in range(max_retries):
            try:
                # 检查是否已存在
                existing = self.supabase.table(table_name).select('id').eq(
                    'google_place_id', poi_data['google_place_id']
                ).execute()
                
                if existing.data:
                    logger.info(f"⏭️  已存在，跳过: {poi_data.get('name')}")
                    self.stats['skipped'] += 1
                    return True
                
                # 写入新数据
                self.supabase.table(table_name).insert(poi_data).execute()
                logger.info(f"✅ 写入成功: {poi_data.get('name')}")
                self.stats['success'] += 1
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️  写入失败，重试 {attempt+1}/{max_retries}: {e}")
                    time.sleep(2 ** attempt)  # 指数退避: 1s, 2s, 4s
                else:
                    logger.error(f"❌ 写入最终失败: {poi_data.get('name')}, 错误: {e}")
                    self.stats['failed'] += 1
                    return False
        
        return False
    
    def retry_from_cache_file(self, json_file: Path) -> Dict:
        """从爬取缓存文件重试写入"""
        logger.info(f"📂 读取缓存文件: {json_file}")
        
        if not json_file.exists():
            logger.error(f"❌ 文件不存在: {json_file}")
            return self.stats
        
        with open(json_file) as f:
            data = json.load(f)
        
        city_id = data.get('city_id', 'unknown')
        logger.info(f"🏙️  城市: {city_id}")
        logger.info(f"📊 数据统计: 餐厅{len(data.get('restaurants', []))}, "
                   f"景点{len(data.get('attractions', []))}, "
                   f"酒店{len(data.get('hotels', []))}")
        
        # 写入餐厅
        for restaurant_data in data.get('restaurants', []):
            self.stats['total'] += 1
            self.write_single_poi(restaurant_data, 'restaurant')
        
        # 写入景点
        for attraction_data in data.get('attractions', []):
            self.stats['total'] += 1
            self.write_single_poi(attraction_data, 'attraction')
        
        # 写入酒店
        for hotel_data in data.get('hotels', []):
            self.stats['total'] += 1
            self.write_single_poi(hotel_data, 'hotel')
        
        return self.stats
    
    def print_summary(self):
        """打印写入统计摘要"""
        logger.info(f"\n{'='*60}")
        logger.info("📊 写入统计摘要")
        logger.info(f"{'='*60}")
        logger.info(f"总数: {self.stats['total']}")
        logger.info(f"✅ 成功: {self.stats['success']}")
        logger.info(f"⏭️  跳过（已存在）: {self.stats['skipped']}")
        logger.info(f"❌ 失败: {self.stats['failed']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] + self.stats['skipped']) / self.stats['total'] * 100
            logger.info(f"📈 成功率: {success_rate:.1f}%")
        
        logger.info(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='重试写入POI数据到Supabase')
    parser.add_argument('--cache-file', type=str, required=True, help='缓存文件路径')
    args = parser.parse_args()
    
    # 从环境变量获取Supabase配置
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("❌ 缺少环境变量: SUPABASE_URL 或 SUPABASE_KEY")
        sys.exit(1)
    
    # 初始化写入器
    try:
        writer = RetryWriter(supabase_url, supabase_key)
        logger.info("✅ Supabase客户端初始化成功")
    except Exception as e:
        logger.error(f"❌ Supabase客户端初始化失败: {e}")
        sys.exit(1)
    
    # 执行重试
    try:
        writer.retry_from_cache_file(Path(args.cache_file))
        writer.print_summary()
        
        # 根据结果设置退出码
        if writer.stats['failed'] > 0:
            logger.warning("⚠️  存在写入失败的记录")
            sys.exit(1)
        else:
            logger.info("🎉 所有数据写入成功！")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ 重试过程出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()