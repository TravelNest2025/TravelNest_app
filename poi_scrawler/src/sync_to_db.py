"""
数据库同步模块
将JSON文件中的POI数据同步到PostgreSQL数据库
"""
import os
import json
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Tuple
from config import DB_CONFIG, CITY_ID, DB_SCHEMA, validate_config

# ==============================================================================
# 数据库连接
# ==============================================================================

def get_db_connection():
    """建立数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connection established")
        return conn
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None


# ==============================================================================
# 数据准备
# ==============================================================================

def prepare_restaurant_data(pois: List[Dict]) -> Tuple[List[str], List[Tuple]]:
    columns = [
        'google_place_id', 'city_id', 'name', 'name_cn',
        'lng', 'lat',  
        'address', 'phone', 'website',
        'rating', 'review_count', 'price_level', 'price_range_label',
        'avg_price_per_person', 'currency',
        'is_michelin', 'michelin_stars',
        'opening_hours', 'photo_urls', 'primary_photo_url',
        'ai_tags', 'categories', 'is_active'
    ]
    
    data_tuples = []
    for poi in pois:
        location = poi.get('location', {})
        
        data_tuple = (
            poi.get('google_place_id'),
            poi.get('city_id', CITY_ID),
            poi.get('name'),
            poi.get('name_cn'),
            location.get('lng'),
            location.get('lat'),
            poi.get('address'),
            poi.get('phone'),
            poi.get('website'),
            poi.get('rating'),
            poi.get('review_count'),
            poi.get('price_level'),
            poi.get('price_range_label'),
            poi.get('avg_price_per_person'),
            poi.get('currency', 'EUR'),
            poi.get('is_michelin', False),
            poi.get('michelin_stars'),
            json.dumps(poi.get('opening_hours')) if poi.get('opening_hours') else None,
            poi.get('photo_urls'),
            poi.get('primary_photo_url'),
            poi.get('ai_tags'),
            poi.get('categories'),
            poi.get('business_status') != 'CLOSED_PERMANENTLY'
        )
        data_tuples.append(data_tuple)
    
    return columns, data_tuples


def prepare_attraction_data(pois: List[Dict]) -> Tuple[List[str], List[Tuple]]:
    columns = [
        'google_place_id', 'city_id', 'name', 'name_cn',
        'lng', 'lat',  # 添加这两个
        'address', 'phone', 'website',
        'rating', 'review_count',
        'ticket_price', 'price_range_label', 'currency', 'is_free_entry',
        'description', 'visit_duration', 'best_time_to_visit',
        'opening_hours', 'photo_urls', 'primary_photo_url',
        'ai_tags', 'categories', 'is_active'
    ]
    
    data_tuples = []
    for poi in pois:
        location = poi.get('location', {})
        
        data_tuple = (
            poi.get('google_place_id'),
            poi.get('city_id', CITY_ID),
            poi.get('name'),
            poi.get('name_cn'),
            location.get('lng'),
            location.get('lat'),
            poi.get('address'),
            poi.get('phone'),
            poi.get('website'),
            poi.get('rating'),
            poi.get('review_count'),
            poi.get('ticket_price'),
            poi.get('price_range_label'),
            poi.get('currency', 'EUR'),
            poi.get('is_free_entry', False),
            poi.get('description'),
            poi.get('visit_duration'),
            poi.get('best_time_to_visit'),
            json.dumps(poi.get('opening_hours')) if poi.get('opening_hours') else None,
            poi.get('photo_urls'),
            poi.get('primary_photo_url'),
            poi.get('ai_tags'),
            poi.get('categories'),
            poi.get('business_status') != 'CLOSED_PERMANENTLY'
        )
        data_tuples.append(data_tuple)
    
    return columns, data_tuples


def prepare_hotel_data(pois: List[Dict]) -> Tuple[List[str], List[Tuple]]:
    columns = [
        'google_place_id', 'city_id', 'name', 'name_cn',
        'lng', 'lat',  # 添加这两个
        'address', 'phone', 'website',
        'rating', 'review_count',
        'price_per_night', 'price_range_label', 'currency',
        'star_rating',
        'photo_urls', 'primary_photo_url',
        'ai_tags', 'categories',
        'booking_url', 'is_active'
    ]
    
    data_tuples = []
    for poi in pois:
        location = poi.get('location', {})
        
        data_tuple = (
            poi.get('google_place_id'),
            poi.get('city_id', CITY_ID),
            poi.get('name'),
            poi.get('name_cn'),
            location.get('lng'),
            location.get('lat'),
            poi.get('address'),
            poi.get('phone'),
            poi.get('website'),
            poi.get('rating'),
            poi.get('review_count'),
            poi.get('price_per_night'),
            poi.get('price_range_label'),
            poi.get('currency', 'EUR'),
            poi.get('star_rating'),
            poi.get('photo_urls'),
            poi.get('primary_photo_url'),
            poi.get('ai_tags'),
            poi.get('categories'),
            poi.get('booking_url'),
            poi.get('business_status') != 'CLOSED_PERMANENTLY'
        )
        data_tuples.append(data_tuple)
    
    return columns, data_tuples


# ==============================================================================
# 数据库操作
# ==============================================================================

def build_upsert_sql(table_name: str, columns: List[str], has_location: bool = True) -> tuple:
    full_table_name = f"{DB_SCHEMA}.{table_name}"
    
    insert_columns = []
    template_parts = []
    
    for col in columns:
        if col == 'lng' or col == 'lat':
            continue
        elif col == 'address' and has_location:
            insert_columns.append('location')
            template_parts.append('ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography')
            insert_columns.append('address')
            template_parts.append('%s')
        else:
            insert_columns.append(col)
            template_parts.append('%s')
    
    insert_cols_str = ', '.join(insert_columns)
    template_str = '(' + ', '.join(template_parts) + ')'
    
    update_clauses = []
    for col in columns:
        if col not in ['google_place_id', 'lng', 'lat']:
            update_clauses.append(f"{col} = EXCLUDED.{col}")
    update_clauses.append('last_updated = CURRENT_TIMESTAMP')
    update_str = ', '.join(update_clauses)
    
    sql = f"""
        INSERT INTO {full_table_name} ({insert_cols_str})
        VALUES %s
        ON CONFLICT (google_place_id) DO UPDATE SET
            {update_str};
    """
    
    return sql, template_str


def upsert_pois(conn, table_name: str, columns: List[str], data_tuples: List[Tuple]) -> int:
    if not data_tuples:
        return 0
    
    try:
        with conn.cursor() as cursor:
            sql, template = build_upsert_sql(table_name, columns, has_location=True)
            
            print(f"\n🔍 Debug Info:")
            print(f"   Table: {table_name}")
            print(f"   Template: {template}")
            
            execute_values(
                cursor,
                sql,
                data_tuples,
                template=template,
                page_size=100
            )
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
    
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        raise


# ==============================================================================
# 主流程
# ==============================================================================

def sync_to_database(json_filepath: str, mode: str = 'upsert'):
    """
    将JSON文件中的数据同步到数据库
    
    Args:
        json_filepath: JSON文件路径
        mode: 同步模式
            - 'upsert': 更新或插入（默认）
            - 'replace': 先删除该城市的所有数据，再插入
    """
    print("\n" + "="*60)
    print("📤 Database Synchronization - Starting")
    print("="*60)
    print(f"   Mode: {mode.upper()}")
    print(f"   City: {CITY_ID}")
    print(f"   File: {json_filepath}")
    print("="*60 + "\n")
    
    # 1. 加载JSON文件
    try:
        # 检查文件是否存在
        if not os.path.exists(json_filepath):
            print(f"❌ File not found: {json_filepath}")
            print(f"   Current directory: {os.getcwd()}")
            print(f"   Files in current directory:")
            for f in os.listdir('.'):
                if f.endswith('.json'):
                    print(f"      - {f}")
            return
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            all_pois = json.load(f)
        print(f"✅ Loaded {len(all_pois)} POIs from {json_filepath}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return
    
    # 2. 按类型分组
    grouped_pois = {
        'restaurant': [],
        'attraction': [],
        'hotel': []
    }
    
    for poi in all_pois:
        poi_type = poi.get('poi_type')
        if poi_type in grouped_pois:
            grouped_pois[poi_type].append(poi)
    
    print(f"\n📊 POI Distribution:")
    for poi_type, pois in grouped_pois.items():
        print(f"   {poi_type.capitalize()}: {len(pois)}")
    
    # 3. 连接数据库
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # 4. 如果是 replace 模式，先清空该城市的数据
        if mode == 'replace':
            clear_city_data(conn, CITY_ID)
        
        total_synced = 0
        
        # 5. 同步餐厅
        if grouped_pois['restaurant']:
            print(f"\n🔄 Syncing {len(grouped_pois['restaurant'])} restaurants...")
            columns, data = prepare_restaurant_data(grouped_pois['restaurant'])
            rows = upsert_pois(conn, 'restaurants', columns, data)
            print(f"✅ Synced {rows} restaurant records")
            total_synced += rows
        
        # 6. 同步景点
        if grouped_pois['attraction']:
            print(f"\n🔄 Syncing {len(grouped_pois['attraction'])} attractions...")
            columns, data = prepare_attraction_data(grouped_pois['attraction'])
            rows = upsert_pois(conn, 'attractions', columns, data)
            print(f"✅ Synced {rows} attraction records")
            total_synced += rows
        
        # 7. 同步酒店
        if grouped_pois['hotel']:
            print(f"\n🔄 Syncing {len(grouped_pois['hotel'])} hotels...")
            columns, data = prepare_hotel_data(grouped_pois['hotel'])
            rows = upsert_pois(conn, 'hotels', columns, data)
            print(f"✅ Synced {rows} hotel records")
            total_synced += rows
        
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS!")
        print(f"{'='*60}")
        print(f"📊 Total records synced: {total_synced}")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"\n❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print("🔌 Database connection closed")


def main():
    """主执行流程"""
    import sys
    import argparse
    
    # 添加命令行参数
    parser = argparse.ArgumentParser(description='Sync POI data to database')
    parser.add_argument(
        '--mode', 
        choices=['upsert', 'replace'], 
        default='upsert',
        help='Sync mode: upsert (update/insert) or replace (delete city data then insert)'
    )
    parser.add_argument(
        '--file', 
        type=str, 
        default=None,
        help='JSON file path'
    )
    
    args = parser.parse_args()
    
    # 验证配置
    if not validate_config(require_db=True, require_apis=False):
        print("\n❌ Configuration validation failed. Exiting...")
        return
    
    # 确定文件路径
    json_filepath = args.file or f"{CITY_ID}_comprehensive_database.json"
    
    # 执行同步
    sync_to_database(json_filepath, mode=args.mode)