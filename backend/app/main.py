"""
FastAPI 应用入口
⭐ 面试考点：
   - CORS：跨域资源共享，前端(localhost:5173)调后端(localhost:8000)必须配置
   - 为什么用 lifespan 而不是 @app.on_event？新版FastAPI推荐方式
   - uvicorn 是 ASGI 服务器，比 WSGI（Flask用的）支持异步，性能更好
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时执行（可以在这里初始化数据库连接等）"""
    print("🚀 简历诊断Agent服务启动")
    yield
    print("👋 服务关闭")


app = FastAPI(
    title="AI 简历诊断 Agent",
    description="基于 ReAct Agent 的智能简历诊断系统",
    version="1.0.0",
    lifespan=lifespan,
)

# ⭐ CORS 配置：允许前端跨域访问
# 生产环境要把 origins 改成你的真实域名，不能用 "*"（安全原则）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite 开发服务器
        "http://localhost:3000",
        "https://*.vercel.app",    # 部署后的 Vercel 域名
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
