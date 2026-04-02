# AI 简历诊断助手

> 基于 ReAct Agent 架构的智能简历分析系统：PDF 解析、职位匹配、流式诊断报告与多轮追问（SSE）。

仓库：<https://github.com/zmytlahz-design/resume-app>

---

## ✨ 功能特性

- **PDF 简历解析** — 自动提取结构化文本
- **ReAct Agent** — 思考 → 工具调用 → 观察，过程实时展示
- **岗位匹配评估** — 对比 JD 输出匹配度与短板分析
- **流式诊断报告** — Markdown，逐段 SSE 推送
- **多轮追问** — 基于会话上下文，仅回答求职相关范围
- **会话持久化** — 会话、对话、工具结果存 **PostgreSQL**；**重置** 时同步删除后端会话数据

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | **Vue 3** + **TypeScript** + **Vite** |
| 状态 | **Pinia**（运行时内存；不做 localStorage 持久化） |
| 后端 | **Python 3.10+** + **FastAPI** |
| 数据库 | **PostgreSQL 16+**，**SQLAlchemy 2**（async）+ **asyncpg** |
| ORM / 迁移依赖 | **Alembic**（依赖已声明，可按需启用迁移） |
| 流式协议 | **SSE**（Server-Sent Events） |
| AI | **智谱 GLM**（OpenAI 兼容 API，默认 `glm-4-flash`） |
| Agent | ReAct + 自定义工具链（PDF / JD 匹配 / 技术栈 / STAR 等） |
| 容器（本地） | **Docker**：PostgreSQL（`启动.bat` 一键拉起） |

---

## 🏗 系统架构（简图）

```
浏览器 (Vue 3, :5173)
    │  fetch /api/* 与 SSE
    ▼
FastAPI (:8011)
    ├── routes：/api/analyze、/api/chat、/api/sessions/{id} …
    ├── ReAct ResumeAgent
    └── PostgreSQL：sessions / messages / tool_results
```

---

## 🚀 快速启动

### 前置条件

- **Python 3.10+**（推荐 3.11）、**Node.js 18+**
- **Docker Desktop**（用于本地 PostgreSQL；也可自备已创建的库）
- 智谱 API Key：<https://open.bigmodel.cn/>

### Windows 一键启动（推荐）

1. 配置 `backend/.env`（可复制 `.env.example` → `backend/.env`，填写 `ZHIPU_API_KEY` 与 `DATABASE_URL`）。
2. 双击项目根目录 **`启动.bat`**：检查环境 → 启动 PostgreSQL 容器 → 后台启动 FastAPI 与 Vite → **等待端口就绪后**再打开浏览器。

日志目录：`logs/backend.log`、`logs/backend.err.log`、`logs/frontend.log`。

### 手动启动（跨平台）

**1. PostgreSQL**

```bash
docker run -d --name resume-postgres -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=resume_app \
  postgres:16-alpine
```

**2. 环境变量**

```bash
cp .env.example backend/.env
# 编辑 backend/.env：ZHIPU_API_KEY、DATABASE_URL（与上一步数据库一致）
```

**3. 后端**

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

应用启动时会 **`create_all()`** 自动建表（开发环境）。

**4. 前端**

```bash
cd frontend
npm install
npm run dev
```

浏览器访问：**http://localhost:5173**（开发时代理 `/api` 到 `8011`，见 `frontend/vite.config.js`）。

---

## 📁 项目结构（节选）

```
resume-app/
├── 启动.bat                 # Windows：Docker PG + 后端 + 前端 + 就绪后打开浏览器
├── scripts/
│   └── wait-for-dev.ps1     # 轮询后端 /api/health 与前端 :5173 后再打开浏览器
├── backend/
│   ├── app/
│   │   ├── agents/resume_agent.py
│   │   ├── api/routes.py           # SSE、会话 REST
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py         # SQLAlchemy async、ORM 模型
│   │   │   ├── db_ops.py           # 会话 / 工具结果持久化
│   │   │   └── redis_client.py     # 遗留模块，主路由未使用
│   │   └── tools/
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/index.ts            # analyzeResume、chat、fetchSession、deleteSession
    │   ├── stores/resume.ts
    │   └── components/             # ResumeUpload、AgentProcess、ReportDisplay、ChatBox …
    └── vite.config.js
```

---

## 🔑 API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 上传 PDF + JD，SSE 流式分析 |
| POST | `/api/chat` | 追问，SSE |
| GET | `/api/sessions/{session_id}` | 拉取会话（消息、工具结果、报告文本） |
| DELETE | `/api/sessions/{session_id}` | 删除会话（前端重置时调用） |
| GET | `/api/health` | 健康检查 |

---

## 🔑 设计要点

1. **ReAct** — Thought → Action → Observation，前端分步展示。  
2. **SSE** — 单向流式，易穿透代理，适合「服务端推、客户端只读」。  
3. **PostgreSQL** — `session_id`（UUID）关联消息与工具结果；会话行含过期时间等字段。  
4. **启动顺序** — `wait-for-dev.ps1` 避免浏览器早于服务就绪出现连接被拒绝。

---

## 📝 License

MIT
