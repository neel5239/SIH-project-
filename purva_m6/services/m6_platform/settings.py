from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "PURVA M6 Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://purva:purva_dev_password@localhost:5432/purva"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    kiosk_api_key: str = "purva-demo-kiosk-key"
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    llm_base_url: str = "http://localhost:8080"
    purva_mock: str = "m1,m2,m3,m4,m5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
