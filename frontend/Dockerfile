# ━━ Stage 1: 构建 Vue 3 应用 ━━━━━━━━━━━━━━
FROM node:20-alpine AS builder

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY package.json ./
RUN npm install

# 复制源码并构建
COPY . .
RUN npm run build

# ━━ Stage 2: Nginx 静态服务 ━━━━━━━━━━━━━━━
FROM nginx:alpine

COPY conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/html /usr/share/nginx/html

EXPOSE 80
