"""Application configuration loaded from environment variables."""
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 使用智谱环境变量命名，避免供应商名称混淆
    # 本地演示允许空值启动；实际调用模型前需提供有效 key。
    llm_api_key: str = Field(default="", alias="ZHIPU_API_KEY")
    llm_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", alias="ZHIPU_BASE_URL")
    llm_model: str = Field(default="glm-4-flash", alias="ZHIPU_MODEL")
    llm_embedding_model: str = Field(default="embedding-3", alias="ZHIPU_EMBEDDING_MODEL")
    redis_host: str = Field(default="127.0.0.1", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
