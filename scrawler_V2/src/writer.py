#!/usr/bin/env python3
"""
独立的Retry Writer - 不依赖其他模块

从缓存文件批量写入POI数据到Supabase
"""

import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetryWriter:
    """带重试机制的POI数据写入器"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        try:
            from supabase import create_client
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ Supabase初始化失败: {e}")
            raise
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }
        self.failed_items = []
    
    def check_exists(self, table: str, google_place_id: str) -> bool:
        """检查POI是否已存在"""
        try:
            result = self.supabase.table(table).select('id').eq(
                'google_place_id', google_place_id
            ).limit(1).execute()
            return len(result.data) > 0
        except:
            return False
    
    def write_single_poi(self, poi_data: Dict, poi_type: str, max_retries: int = 3) -> bool:
        """写入单个POI（带重试）"""
        table_map = {
            'restaurant': 'restaurants',
            'attraction': 'attractions',
            'hotel': 'hotels',
        }
        
        table = table_map.get(poi_type)
        if not table:
            logger.error(f"❌ 未知POI类型: {poi_type}")
            return False
        
        google_place_id = poi_data.get('google_place_id')
        name = poi_data.get('name', 'Unknown')
        
        # 检查是否已存在
        if self.check_exists(table, google_place_id):
            logger.debug(f"⏭️  跳过已存在: {name}")
            self.stats['skipped'] += 1
            return True
        
        # 尝试写入（带重试）
        for attempt in range(max_retries):
            try:
                result = self.supabase.table(table).insert(poi_data).execute()
                
                if result.data:
                    logger.debug(f"✅ 写入成功: {name}")
                    self.stats['success'] += 1
                    return True
            
            except Exception as e:
                logger.warning(f"⚠️  写入失败 (尝试 {attempt + 1}/{max_retries}): {name}")
                
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt  # 指数退避
                    time.sleep(sleep_time)
                else:
                    logger.error(f"❌ 最终失败: {name} - {e}")
                    self.stats['failed'] += 1
                    self.failed_items.append({
                        'type': poi_type,
                        'name': name,
                        'google_place_id': google_place_id,
                        'error': str(e)
                    })
                    return False
        
        return False
    
    def write_from_cache(self, cache_file: str) -> Dict:
        """从缓存文件读取并批量写入"""
        logger.info(f"📂 读取缓存文件: {cache_file}")
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {e}")
            raise
        
        restaurants = data.get('restaurants', [])
        attractions = data.get('attractions', [])
        hotels = data.get('hotels', [])
        
        total = len(restaurants) + len(attractions) + len(hotels)
        self.stats['total'] = total
        
        logger.info(f"\n📊 总计: {total} 个POI")
        logger.info(f"   餐厅: {len(restaurants)}")
        logger.info(f"   景点: {len(attractions)}")
        logger.info(f"   酒店: {len(hotels)}")
        
        # 写入餐厅
        if restaurants:
            logger.info(f"\n💾 写入餐厅 ({len(restaurants)}个)...")
            for i, poi in enumerate(restaurants, 1):
                logger.info(f"[{i}/{len(restaurants)}] {poi.get('name')}")
                self.write_single_poi(poi, 'restaurant')
        
        # 写入景点
        if attractions:
            logger.info(f"\n🎭 写入景点 ({len(attractions)}个)...")
            for i, poi in enumerate(attractions, 1):
                logger.info(f"[{i}/{len(attractions)}] {poi.get('name')}")
                self.write_single_poi(poi, 'attraction')
        
        # 写入酒店
        if hotels:
            logger.info(f"\n🏨 写入酒店 ({len(hotels)}个)...")
            for i, poi in enumerate(hotels, 1):
                logger.info(f"[{i}/{len(hotels)}] {poi.get('name')}")
                self.write_single_poi(poi, 'hotel')
        
        # 保存失败记录
        if self.failed_items:
            failed_file = 'cache/failed_writes.json'
            os.makedirs('cache', exist_ok=True)
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_items, f, indent=2, ensure_ascii=False)
            logger.warning(f"⚠️  失败记录: {failed_file}")
        
        return self.stats
    
    def print_summary(self):
        """打印总结"""
        print("\n" + "="*60)
        print("  📊 写入总结")
        print("="*60)
        print(f"总计:     {self.stats['total']:>6}")
        print(f"✅ 成功:  {self.stats['success']:>6}")
        print(f"⏭️  跳过:  {self.stats['skipped']:>6} (已存在)")
        print(f"❌ 失败:  {self.stats['failed']:>6}")
        print("="*60)
        
        if self.stats['failed'] > 0:
            print(f"\n⚠️  {self.stats['failed']} 个POI写入失败")
            print("详情: cache/failed_writes.json")
        elif self.stats['success'] > 0:
            print("\n🎉 所有POI写入成功！")


def main():
    parser = argparse.ArgumentParser(description='从缓存文件批量写入POI')
    parser.add_argument('--cache-file', required=True, help='缓存JSON文件路径')
    args = parser.parse_args()
    
    if not os.path.exists(args.cache_file):
        logger.error(f"❌ 文件不存在: {args.cache_file}")
        sys.exit(1)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("❌ 缺少环境变量: SUPABASE_URL, SUPABASE_KEY")
        sys.exit(1)
    
    try:
        writer = RetryWriter(supabase_url, supabase_key)
        writer.write_from_cache(args.cache_file)
        writer.print_summary()
        
        if writer.stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()