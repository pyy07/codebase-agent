#!/bin/bash
# 停止脚本

set -e

ENV=${1:-prod}

if [ "$ENV" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

echo "🛑 停止 Codebase Driven Agent..."
docker-compose -f $COMPOSE_FILE down

echo "✅ 服务已停止"

