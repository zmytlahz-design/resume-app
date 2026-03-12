# AI 简历诊断 Agent - 启动脚本
# 用法：
#   .\启动.ps1          → 生产模式（全 Docker）
#   .\启动.ps1 dev      → 开发模式（backend/redis 用 Docker，前端 npm run dev）
#   .\启动.ps1 stop     → 停止所有服务
#   .\启动.ps1 build    → 重新构建镜像并启动

param(
    [string]$mode = "prod"
)

$PROJECT = "resume-app"
$FRONTEND_DIR = "$PSScriptRoot\frontend"

function Write-Step($msg) {
    Write-Host "`n▶ $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Err($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

# ── 检查 Docker ────────────────────────────────────────────────
function Check-Docker {
    Write-Step "检查 Docker..."
    try {
        $v = docker version --format "{{.Server.Version}}" 2>$null
        Write-OK "Docker $v 运行正常"
    } catch {
        Write-Err "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    }
}

# ── 停止所有服务 ───────────────────────────────────────────────
function Stop-Services {
    Write-Step "停止所有服务..."
    docker-compose -p $PROJECT down
    Write-OK "服务已停止"
}

# ── 构建镜像 ───────────────────────────────────────────────────
function Build-Images([bool]$frontendOnly = $false) {
    if ($frontendOnly) {
        Write-Step "构建前端镜像..."
        docker-compose -p $PROJECT build frontend
    } else {
        Write-Step "构建所有镜像..."
        docker-compose -p $PROJECT build
    }
}

# ── 启动后端服务（Docker）─────────────────────────────────────
function Start-Backend {
    Write-Step "启动 Redis + Backend..."
    docker-compose -p $PROJECT up -d redis backend
    
    # 等待 backend 健康
    $retry = 0
    while ($retry -lt 15) {
        Start-Sleep -Seconds 2
        $status = docker inspect --format "{{.State.Status}}" resume-backend 2>$null
        if ($status -eq "running") {
            $log = docker logs resume-backend 2>&1 | Select-String "Application startup complete"
            if ($log) {
                Write-OK "Backend 已就绪 → http://localhost:8011"
                return
            }
        } elseif ($status -eq "restarting") {
            Write-Err "Backend 启动失败，查看日志："
            docker logs resume-backend 2>&1 | Select-Object -Last 15
            exit 1
        }
        $retry++
        Write-Host "  等待 backend 启动... ($($retry * 2)s)" -ForegroundColor Yellow
    }
    Write-Err "Backend 启动超时"
    exit 1
}

# ── 启动全部服务（生产模式）───────────────────────────────────
function Start-Prod {
    docker-compose -p $PROJECT up -d
    
    Start-Sleep -Seconds 5
    $all_up = $true
    foreach ($name in @("resume-redis", "resume-backend", "resume-frontend")) {
        $status = docker inspect --format "{{.State.Status}}" $name 2>$null
        if ($status -ne "running") {
            Write-Err "$name 状态异常: $status"
            $all_up = $false
        } else {
            Write-OK "$name 运行中"
        }
    }

    if ($all_up) {
        Write-Host "`n🎉 启动成功！访问 " -NoNewline -ForegroundColor Green
        Write-Host "http://localhost" -ForegroundColor Yellow
    }
}

# ── 启动前端开发服务器 ─────────────────────────────────────────
function Start-DevFrontend {
    Write-Step "启动前端开发服务器 (npm run dev)..."

    if (-not (Test-Path "$FRONTEND_DIR\node_modules")) {
        Write-Host "  首次运行，安装依赖..." -ForegroundColor Yellow
        Push-Location $FRONTEND_DIR
        npm install
        Pop-Location
    }

    Write-OK "Frontend 开发服务器启动中..."
    Write-Host "`n🎉 开发模式启动成功！" -ForegroundColor Green
    Write-Host "   前端：" -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Yellow
    Write-Host "   后端：" -NoNewline; Write-Host "http://localhost:8011" -ForegroundColor Yellow
    Write-Host ""

    Push-Location $FRONTEND_DIR
    npm run dev
    Pop-Location
}

# ══════════════════════════════════════════════════════════════
#  主逻辑
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "╔══════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║   AI 简历诊断 Agent 启动脚本     ║" -ForegroundColor Blue
Write-Host "╚══════════════════════════════════╝" -ForegroundColor Blue

Check-Docker

switch ($mode.ToLower()) {

    "stop" {
        Stop-Services
    }

    "build" {
        Stop-Services
        Build-Images
        Start-Prod
    }

    "dev" {
        Write-Host "`n  模式：开发模式（前端热更新）" -ForegroundColor Magenta
        Start-Backend
        Start-DevFrontend   # 阻塞在这里，Ctrl+C 退出
    }

    default {
        Write-Host "`n  模式：生产模式（全 Docker）" -ForegroundColor Magenta
        Start-Prod
    }
}
