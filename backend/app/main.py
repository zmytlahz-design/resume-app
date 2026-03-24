"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时执行（可以在这里初始化数据库连接等）"""
    print("Resume Agent service started")
    yield
    print("Resume Agent service stopped")


app = FastAPI(
    title="AI 简历诊断 Agent",
    description="基于 ReAct Agent 的智能简历诊断系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for local dev and deployed frontend origins.
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
