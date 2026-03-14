"""
配置管理
⭐ 面试考点：为什么用 pydantic-settings？
   - 类型自动校验，环境变量读取安全
   - 比直接 os.getenv() 更规范，生产项目标准做法

实际可接智谱 GLM、DeepSeek 等兼容 OpenAI 的接口，通过 .env 的 base_url / model 切换。
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 兼容旧 .env 的 DEEPSEEK_* 变量名，实际可用智谱等
    llm_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    llm_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", alias="DEEPSEEK_BASE_URL")
    llm_model: str = Field(default="glm-4-flash", alias="DEEPSEEK_MODEL")
    llm_embedding_model: str = Field(default="embedding-3", alias="DEEPSEEK_EMBEDDING_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


@lru_cache()  # 单例模式，全局只读一次 .env
def get_settings() -> Settings:
    return Settings()
