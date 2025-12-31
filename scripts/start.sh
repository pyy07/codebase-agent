#!/bin/bash
# 一键启动脚本

set -e

echo "🚀 Codebase Driven Agent - 启动脚本"
echo "=================================="

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 创建..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 已创建 .env 文件，请编辑后重新运行"
        exit 1
    else
        echo "❌ .env.example 文件不存在"
        exit 1
    fi
fi

# 选择环境
ENV=${1:-prod}

if [ "$ENV" = "dev" ]; then
    echo "📦 使用开发环境配置..."
    COMPOSE_FILE="docker-compose.dev.yml"
else
    echo "📦 使用生产环境配置..."
    COMPOSE_FILE="docker-compose.yml"
fi

# 构建并启动
echo "🔨 构建 Docker 镜像..."
docker-compose -f $COMPOSE_FILE build

echo "🚀 启动服务..."
docker-compose -f $COMPOSE_FILE up -d

echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose -f $COMPOSE_FILE ps

# 检查健康状态
echo "🏥 检查健康状态..."
for i in {1..30}; do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" &> /dev/null 2>&1 || curl -f http://localhost:8000/health &> /dev/null 2>&1; then
        echo "✅ 服务已启动并健康！"
        echo ""
        echo "📝 访问信息："
        echo "   - API 文档: http://localhost:8000/docs"
        echo "   - 健康检查: http://localhost:8000/health"
        echo "   - 服务信息: http://localhost:8000/api/v1/info"
        echo ""
        echo "📋 查看日志: docker-compose -f $COMPOSE_FILE logs -f"
        echo "🛑 停止服务: docker-compose -f $COMPOSE_FILE down"
        exit 0
    fi
    sleep 1
done

echo "⚠️  服务启动超时，请检查日志: docker-compose -f $COMPOSE_FILE logs"
exit 1

