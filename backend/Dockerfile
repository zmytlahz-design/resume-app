# ① 基础镜像：python:3.11-slim
#    - 3.11 而非本地的 3.14：numpy/pydantic 等包在 3.11 有预编译 wheel，装得快
#    - slim 版本去掉了编译工具链、文档等，比 full 镜像小约 700MB
FROM python:3.11-slim

# ② 设置容器内的工作目录
#    后续 COPY / RUN / CMD 都以 /app 为起点
WORKDIR /app

# ③ 先只复制依赖文件，不复制业务代码
#    Docker 构建是分层的，每条指令产生一层缓存
#    只要 requirements.txt 不变，下面的 pip install 层就会命中缓存
#    这样改了业务代码重新构建时，不用重新下载所有依赖——节省大量时间
COPY requirements.txt .

# ④ 安装 Python 依赖
#    --no-cache-dir：不保留 pip 下载缓存，避免镜像里有无用文件（减小体积）
RUN pip install --no-cache-dir -r requirements.txt

# ⑤ 复制业务代码（放在依赖安装之后）
#    因为代码改动比依赖改动频繁，放最后可以最大化利用层缓存
COPY . .

# ⑥ 声明容器对外暴露的端口（仅文档作用，不实际开放端口）
#    docker-compose 里的 ports 才是真正映射宿主机端口的地方
EXPOSE 8011

# ⑦ 容器启动命令
#    用 CMD 而非 RUN：RUN 是构建时执行，CMD 是容器启动时执行
#    --host 0.0.0.0：监听所有网卡，否则只监听 127.0.0.1，容器外无法访问
#    不加 --reload：生产环境不需要热重载，减少资源消耗
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
