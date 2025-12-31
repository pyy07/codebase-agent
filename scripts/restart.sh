#!/bin/bash
# 重启脚本

set -e

ENV=${1:-prod}

if [ "$ENV" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

echo "🔄 重启 Codebase Driven Agent..."
docker-compose -f $COMPOSE_FILE restart

echo "✅ 服务已重启"

