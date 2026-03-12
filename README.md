# AI 简历诊断助手

> 基于 ReAct Agent 架构的智能简历分析系统，支持 PDF 解析、职位匹配评估与多轮追问对话，全程流式输出。

---

## ✨ 功能特性

- **PDF 简历解析** — 自动提取结构化文本信息
- **ReAct Agent 分析** — 逐步推理（思考→工具调用→观察），过程实时可见
- **岗位匹配评估** — 对比 JD 自动评分，输出技能匹配度与短板分析
- **流式诊断报告** — Markdown 格式，逐字流式渲染
- **多轮追问对话** — 基于简历上下文，仅回答求职相关问题
- **刷新不丢状态** — 全部分析结果持久化到 localStorage

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite |
| 前端状态 | Pinia（持久化到 localStorage）|
| 前端渲染 | Nginx（反向代理 `/api`）|
| 后端框架 | Python FastAPI |
| 流式协议 | SSE（Server-Sent Events）|
| AI Agent | ReAct 架构（自定义工具链）|
| 大语言模型 | GLM-4-Flash（智谱 AI）|
| 会话存储 | Redis（2h TTL 自动过期）|
| 容器编排 | Docker Compose |

---

## 🏗 系统架构

```
浏览器
  │
  ├─ 静态资源（Vue3 SPA）─── Nginx :80
  │
  └─ /api/* ──────────────── Nginx 反向代理
                                  │
                             FastAPI :8011
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
               ReAct Agent                   Redis
               （pdf_parser                 session / cache
                jd_matcher                  2h TTL
                stack_checker）
```

---

## 🚀 快速启动

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安装并运行

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/resume-app.git
cd resume-app
```

### 2. 配置 API Key

```bash
# 复制示例文件
cp .env.example backend/.env

# 编辑 backend/.env，填入你的智谱 AI API Key
# 申请地址：https://open.bigmodel.cn/
```

`.env` 内容示例：
```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://open.bigmodel.cn/api/paas/v4
DEEPSEEK_MODEL=glm-4-flash
DEEPSEEK_EMBEDDING_MODEL=embedding-3
```

### 3. 启动服务

```bash
docker-compose up -d --build
```

等待构建完成后，访问：**http://localhost**

### 4. 停止服务

```bash
docker-compose down
```

---

## 📁 项目结构

```
resume-app/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── agents/
│   │   │   └── resume_agent.py   # ReAct Agent 核心逻辑
│   │   ├── api/
│   │   │   └── routes.py         # SSE 流式接口
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic 配置管理
│   │   │   └── redis_client.py   # Redis 会话封装
│   │   └── tools/
│   │       ├── pdf_parser.py     # PDF 解析工具
│   │       ├── jd_matcher.py     # JD 匹配工具
│   │       └── stack_checker.py  # 技术栈检查工具
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── api/index.js          # SSE 流式请求封装
│   │   ├── stores/resume.js      # Pinia 状态管理
│   │   └── components/
│   │       ├── ResumeUpload.vue  # 上传 & 触发分析
│   │       ├── AgentProcess.vue  # Agent 思考步骤展示
│   │       ├── ReportDisplay.vue # 诊断报告渲染
│   │       └── ChatBox.vue       # 追问对话框
│   ├── Dockerfile
│   └── vite.config.js
└── docker-compose.yml
```

---

## 🔑 核心设计亮点

### 1. ReAct Agent 架构
Agent 在每一轮迭代中依次执行**思考（Thought）→ 工具调用（Action）→ 观察结果（Observation）**，逻辑清晰可追溯，前端实时展示每一步。

### 2. SSE 流式输出
使用 HTTP SSE 协议（而非 WebSocket）实现服务端到客户端的单向数据推送，无需握手升级，天然兼容 HTTP/2，适合"服务端持续推送、客户端只读"的场景。

### 3. Redis 会话隔离
每个用户分配唯一 `session_id`（UUID），对话历史存入 Redis（`session:{id}`），PDF 解析结果单独缓存（`cache:{id}`），2 小时自动过期，天然支持水平扩展。

### 4. Vue 3 响应式持久化
分析结果（Agent 步骤、诊断报告、聊天记录）写入 `localStorage`，刷新页面无需重新分析，解决 SPA 状态丢失问题。

---

## 📝 License

MIT
