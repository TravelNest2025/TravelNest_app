"""
数据库同步模块
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import json

from .config import Config

class Database:
    """数据库管理类"""
    
    def __init__(self):
        self.conn_params = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'dbname': Config.DB_NAME,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'connect_timeout': 10,
            'options': f'-c search_path={Config.DB_SCHEMA},public'
        }
        print(f"Database initialized: {Config.DB_NAME}@{Config.DB_HOST}")
        print(f"Schema: {Config.DB_SCHEMA}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {Config.DB_SCHEMA}, public")
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT current_schema()")
                    schema = cur.fetchone()[0]
                    print(f"✅ Database connection successful")
                    print(f"   Current schema: {schema}")
                    return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def get_city_config(self, city_id: str) -> Optional[Dict[str, Any]]:
        """获取城市配置"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        city_id, city_name, city_name_cn, region,
                        ST_X(center_location::geometry) as longitude,
                        ST_Y(center_location::geometry) as latitude,
                        search_radius
                    FROM city_config
                    WHERE city_id = %s AND is_active = TRUE
                """, (city_id,))
                
                result = cur.fetchone()
                if result:
                    print(f"✅ Found city: {result['city_name']}")
                else:
                    print(f"⚠️  City '{city_id}' not found")
                
                return dict(result) if result else None
    
    def get_category_mappings(self) -> Dict[str, Dict[str, Any]]:
        """获取分类映射"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT google_type, mapped_categories, confidence
                    FROM google_type_category_mapping
                    WHERE is_active = TRUE AND confidence >= 0.70
                    ORDER BY priority DESC
                """)
                
                mappings = {}
                for row in cur.fetchall():
                    mappings[row['google_type']] = {
                        'categories': row['mapped_categories'],
                        'confidence': float(row['confidence'])
                    }
                
                print(f"✅ Loaded {len(mappings)} mappings")
                return mappings
    
    def bulk_insert_pois(self, table_name: str, pois: List[Dict[str, Any]]) -> tuple[int, int]:
        """批量插入 POIs"""
        if not pois:
            return 0, 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    columns = list(pois[0].keys())
                    columns_str = ', '.join(columns)
                    
                    values = []
                    for poi in pois:
                        row = []
                        for col in columns:
                            val = poi.get(col)
                            if col in ['google_types', 'categories', 'photo_urls', 'opening_hours'] and val:
                                if isinstance(val, (list, dict)):
                                    val = json.dumps(val)
                            row.append(val)
                        values.append(row)
                    
                    update_cols = [c for c in columns if c not in ['id', 'google_place_id', 'created_at']]
                    update_str = ', '.join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                    
                    query = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES %s
                        ON CONFLICT (google_place_id)
                        DO UPDATE SET {update_str}, last_updated = CURRENT_TIMESTAMP
                    """
                    
                    execute_values(cur, query, values)
                    
                    print(f"   ✅ Saved {len(pois)} POIs to {table_name}")
                    return len(pois), 0
        
        except Exception as e:
            print(f"   ❌ Insert failed: {e}")
            return 0, 0