"""
配置管理模块
"""
import os

class Config:
    """应用配置"""
    
    # 数据库配置
    DB_HOST: str = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    DB_NAME: str = os.getenv('DB_NAME', 'poi_data')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
    # Google Cloud SQL 配置
    GCSQL_INSTANCE_NAME: str = os.getenv('GCSQL_INSTANCE_NAME', '')
    GCP_PROJECT_ID: str = os.getenv('GCP_PROJECT_ID', '')
    
    # 采集配置
    DEFAULT_SEARCH_RADIUS: int = 25000
    MAX_RESULTS_PER_REQUEST: int = 20
    REQUEST_DELAY: float = 0.3
    BATCH_SIZE: int = 10
    
    @classmethod
    def get_database_url(cls) -> str:
        """获取数据库连接 URL"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def validate(cls) -> None:
        """验证必需的配置"""
        errors = []
        
        if not cls.GOOGLE_MAPS_API_KEY:
            errors.append("GOOGLE_MAPS_API_KEY is required")
        
        if not cls.DB_PASSWORD:
            errors.append("DB_PASSWORD is required")
        
        if not cls.DB_NAME:
            errors.append("DB_NAME is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        print("✅ Configuration validated")
        print(f"   - Database: {cls.DB_NAME}@{cls.DB_HOST}:{cls.DB_PORT}")
        print(f"   - API Key: {cls.GOOGLE_MAPS_API_KEY[:20]}...")