"""
配置管理
⭐ 面试考点：为什么用 pydantic-settings？
   - 类型自动校验，环境变量读取安全
   - 比直接 os.getenv() 更规范，生产项目标准做法
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    deepseek_api_key: str
    deepseek_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    deepseek_model: str = "glm-4-flash"
    deepseek_embedding_model: str = "embedding-3"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()  # 单例模式，全局只读一次 .env
def get_settings() -> Settings:
    return Settings()
