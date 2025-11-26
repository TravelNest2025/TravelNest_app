"""
POI数据写入模块

将爬取的数据写入Supabase数据库
"""

import logging
from typing import List
from supabase import create_client, Client
import time

from models import Restaurant, Attraction, Hotel, CrawlResult, WriteResult
from config import SupabaseConfig, WriterConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupabaseWriter:
    """Supabase数据库写入器"""
    
    def __init__(
        self,
        supabase_config: SupabaseConfig,
        writer_config: WriterConfig,
    ):
        self.supabase_config = supabase_config
        self.writer_config = writer_config
        
        # 初始化Supabase客户端
        self.client: Client = create_client(
            supabase_config.url,
            supabase_config.key
        )
        
        logger.info(f"✅ Supabase客户端初始化成功: {supabase_config.url}")
    
    def write_crawl_result(self, crawl_result: CrawlResult) -> WriteResult:
        """
        写入整个爬取结果
        
        Args:
            crawl_result: 爬取结果
            
        Returns:
            写入结果统计
        """
        logger.info(f"🚀 开始写入数据到Supabase...")
        
        write_result = WriteResult()
        
        # 1. 写入餐厅
        if crawl_result.restaurants:
            logger.info(f"📝 写入 {len(crawl_result.restaurants)} 个餐厅...")
            result = self._write_pois(crawl_result.restaurants, 'restaurants')
            write_result.success_count += result.success_count
            write_result.failed_count += result.failed_count
            write_result.skipped_count += result.skipped_count
            write_result.errors.extend(result.errors)
        
        # 2. 写入景点
        if crawl_result.attractions:
            logger.info(f"📝 写入 {len(crawl_result.attractions)} 个景点...")
            result = self._write_pois(crawl_result.attractions, 'attractions')
            write_result.success_count += result.success_count
            write_result.failed_count += result.failed_count
            write_result.skipped_count += result.skipped_count
            write_result.errors.extend(result.errors)
        
        # 3. 写入酒店
        if crawl_result.hotels:
            logger.info(f"📝 写入 {len(crawl_result.hotels)} 个酒店...")
            result = self._write_pois(crawl_result.hotels, 'hotels')
            write_result.success_count += result.success_count
            write_result.failed_count += result.failed_count
            write_result.skipped_count += result.skipped_count
            write_result.errors.extend(result.errors)
        
        logger.info(f"✅ 写入完成！成功: {write_result.success_count}, "
                   f"失败: {write_result.failed_count}, "
                   f"跳过: {write_result.skipped_count}")
        
        return write_result
    
    def _write_pois(
        self,
        pois: List[Restaurant | Attraction | Hotel],
        table_name: str
    ) -> WriteResult:
        """
        批量写入POI数据
        
        Args:
            pois: POI列表
            table_name: 表名
            
        Returns:
            写入结果
        """
        result = WriteResult()
        
        # 分批处理
        batch_size = self.writer_config.batch_size
        for i in range(0, len(pois), batch_size):
            batch = pois[i:i + batch_size]
            batch_result = self._write_batch(batch, table_name)
            
            result.success_count += batch_result.success_count
            result.failed_count += batch_result.failed_count
            result.skipped_count += batch_result.skipped_count
            result.errors.extend(batch_result.errors)
            
            # 批次间延迟
            if i + batch_size < len(pois):
                time.sleep(0.5)
        
        return result
    
    def _write_batch(
        self,
        pois: List[Restaurant | Attraction | Hotel],
        table_name: str
    ) -> WriteResult:
        """
        写入一个批次的POI
        
        Args:
            pois: POI列表
            table_name: 表名
            
        Returns:
            写入结果
        """
        result = WriteResult()
        
        for poi in pois:
            try:
                # 转换为数据库格式
                data = poi.to_db_dict()
                
                # 检查是否已存在
                if self.writer_config.skip_existing:
                    existing = self.client.table(table_name).select('id').eq(
                        'google_place_id', poi.google_place_id
                    ).execute()
                    
                    if existing.data:
                        if self.writer_config.update_existing:
                            # 更新已存在的记录
                            self.client.table(table_name).update(data).eq(
                                'google_place_id', poi.google_place_id
                            ).execute()
                            result.success_count += 1
                            logger.debug(f"✅ 更新: {poi.name}")
                        else:
                            # 跳过已存在的记录
                            result.skipped_count += 1
                            logger.debug(f"⏭️  跳过（已存在）: {poi.name}")
                        continue
                
                # 插入新记录
                self.client.table(table_name).insert(data).execute()
                result.success_count += 1
                logger.debug(f"✅ 插入: {poi.name}")
                
            except Exception as e:
                result.failed_count += 1
                error_info = {
                    'poi_name': poi.name,
                    'google_place_id': poi.google_place_id,
                    'error': str(e),
                }
                result.errors.append(error_info)
                logger.error(f"❌ 写入失败: {poi.name} - {e}")
        
        return result
    
    def verify_city_config(self, city_id: str) -> bool:
        """
        验证城市配置是否存在于数据库
        
        Args:
            city_id: 城市ID
            
        Returns:
            True if exists
        """
        try:
            result = self.client.table('city_config').select('city_id').eq(
                'city_id', city_id
            ).execute()
            
            exists = bool(result.data)
            if exists:
                logger.info(f"✅ 城市配置已存在: {city_id}")
            else:
                logger.warning(f"⚠️  城市配置不存在: {city_id}")
                logger.warning("请先在数据库中创建城市配置记录")
            
            return exists
        
        except Exception as e:
            logger.error(f"❌ 验证城市配置失败: {e}")
            return False
    
    def get_existing_place_ids(self, table_name: str, city_id: str) -> set:
        """
        获取已存在的place ID集合（用于去重）
        
        Args:
            table_name: 表名
            city_id: 城市ID
            
        Returns:
            place_id集合
        """
        try:
            result = self.client.table(table_name).select('google_place_id').eq(
                'city_id', city_id
            ).execute()
            
            place_ids = {row['google_place_id'] for row in result.data}
            logger.info(f"📊 {table_name}表中已有 {len(place_ids)} 条记录（城市: {city_id}）")
            
            return place_ids
        
        except Exception as e:
            logger.error(f"❌ 获取已存在记录失败: {e}")
            return set()
    
    def get_statistics(self, city_id: str = None) -> dict:
        """
        获取数据库统计信息
        
        Args:
            city_id: 城市ID（可选，None表示所有城市）
            
        Returns:
            统计信息字典
        """
        stats = {
            'restaurants': 0,
            'attractions': 0,
            'hotels': 0,
            'total': 0,
        }
        
        try:
            for table in ['restaurants', 'attractions', 'hotels']:
                query = self.client.table(table).select('id', count='exact')
                
                if city_id:
                    query = query.eq('city_id', city_id)
                
                result = query.execute()
                count = result.count if hasattr(result, 'count') else len(result.data)
                stats[table] = count
            
            stats['total'] = sum([stats['restaurants'], stats['attractions'], stats['hotels']])
            
            return stats
        
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return stats


# ==========================================
# 命令行入口
# ==========================================

if __name__ == '__main__':
    import sys
    import json
    from config import get_supabase_config, get_writer_config
    from models import CrawlResult
    
    # 解析命令行参数
    input_file = sys.argv[1] if len(sys.argv) > 1 else './cache/paris_crawl_result.json'
    
    # 初始化配置
    supabase_config = get_supabase_config()
    writer_config = get_writer_config()
    
    # 创建写入器
    writer = SupabaseWriter(supabase_config, writer_config)
    
    try:
        # 加载爬取结果
        logger.info(f"📂 加载爬取结果: {input_file}")
        crawl_result = CrawlResult.load_from_file(input_file)
        
        logger.info(f"📊 加载数据:")
        logger.info(f"  - 餐厅: {len(crawl_result.restaurants)}")
        logger.info(f"  - 景点: {len(crawl_result.attractions)}")
        logger.info(f"  - 酒店: {len(crawl_result.hotels)}")
        logger.info(f"  - 总计: {crawl_result.total_pois}")
        
        # 验证城市配置
        if not writer.verify_city_config(crawl_result.city_id):
            logger.error("❌ 城市配置验证失败，退出")
            sys.exit(1)
        
        # 执行写入
        write_result = writer.write_crawl_result(crawl_result)
        
        # 打印结果
        print("\n=== 写入结果 ===")
        print(f"成功: {write_result.success_count}")
        print(f"失败: {write_result.failed_count}")
        print(f"跳过: {write_result.skipped_count}")
        
        if write_result.errors:
            print(f"\n失败详情:")
            for error in write_result.errors[:10]:  # 只打印前10个错误
                print(f"  - {error['poi_name']}: {error['error']}")
        
        # 获取数据库统计
        stats = writer.get_statistics(crawl_result.city_id)
        print(f"\n=== 数据库统计（{crawl_result.city_id}）===")
        print(f"餐厅: {stats['restaurants']}")
        print(f"景点: {stats['attractions']}")
        print(f"酒店: {stats['hotels']}")
        print(f"总计: {stats['total']}")
        
    except FileNotFoundError:
        logger.error(f"❌ 文件不存在: {input_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 写入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)