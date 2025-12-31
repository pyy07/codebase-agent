# 部署指南

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+（或 Docker Compose V2）
- 至少 2GB 可用内存
- 至少 5GB 可用磁盘空间

### 一键启动（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写必要的配置（至少配置 LLM API Key）

# 2. 一键启动（生产环境）
chmod +x scripts/start.sh
./scripts/start.sh

# 或使用开发环境
./scripts/start.sh dev
```

### 手动启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 2. 构建并启动（生产环境）
docker-compose up -d

# 或开发环境（支持热重载）
docker-compose -f docker-compose.dev.yml up -d
```

## 环境配置

### 必需配置

至少需要配置以下之一：
- `OPENAI_API_KEY` - OpenAI API Key
- `ANTHROPIC_API_KEY` - Anthropic API Key

### 可选配置

根据实际需求配置：
- **日志易**: `LOGYI_BASE_URL`, `LOGYI_USERNAME`, `LOGYI_APIKEY`, `LOGYI_APPNAME`
- **数据库**: `DATABASE_URL`
- **代码仓库**: `CODE_REPO_PATH`（挂载本地代码库路径）
- **文件日志**: `LOG_FILE_BASE_PATH`（挂载日志文件路径）

## 服务管理

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f agent
docker-compose logs -f redis
```

### 停止服务

```bash
# 使用脚本
./scripts/stop.sh

# 或手动
docker-compose down
```

### 重启服务

```bash
# 使用脚本
./scripts/restart.sh

# 或手动
docker-compose restart
```

### 重建服务

```bash
# 重新构建并启动
docker-compose up -d --build
```

## 目录结构

```
.
├── Dockerfile              # 生产环境 Dockerfile
├── Dockerfile.dev          # 开发环境 Dockerfile
├── docker-compose.yml      # 生产环境配置
├── docker-compose.dev.yml  # 开发环境配置
├── .dockerignore           # Docker 忽略文件
├── .env.example            # 环境变量示例
├── scripts/
│   ├── start.sh            # 启动脚本
│   ├── stop.sh             # 停止脚本
│   └── restart.sh          # 重启脚本
└── codebase_driven_agent/  # 应用代码
```

## 数据卷挂载

### 代码仓库挂载

如果需要 Agent 访问本地代码库：

```yaml
# docker-compose.yml
volumes:
  - /path/to/your/codebase:/app/codebase:ro
```

或在 `.env` 中配置：
```bash
CODE_REPO_PATH=/path/to/your/codebase
```

### 日志文件挂载

如果使用文件日志查询：

```yaml
volumes:
  - /path/to/logs:/app/logs:ro
```

或在 `.env` 中配置：
```bash
LOG_FILE_BASE_PATH=/path/to/logs
```

## 网络配置

服务默认使用 `agent-network` 网络，Redis 服务可通过 `redis:6379` 访问。

## 健康检查

服务包含健康检查端点：
- HTTP: `GET http://localhost:8000/health`

Docker 会自动监控服务健康状态。

## 生产环境建议

1. **使用环境变量文件**: 不要将 `.env` 文件提交到版本控制
2. **配置 API Key**: 确保设置了有效的 LLM API Key
3. **资源限制**: 根据需要调整 Docker 资源限制
4. **日志管理**: 配置日志轮转和存储
5. **监控**: 集成监控系统（Prometheus、Grafana 等）
6. **备份**: 定期备份 Redis 数据（如果使用 Redis 存储）

## 故障排查

### 服务无法启动

1. 检查 Docker 和 Docker Compose 版本
2. 查看日志: `docker-compose logs agent`
3. 检查端口占用: `netstat -tuln | grep 8000`
4. 检查环境变量配置

### 健康检查失败

1. 检查服务日志
2. 确认端口映射正确
3. 检查防火墙设置

### Redis 连接失败

1. 确认 Redis 服务已启动: `docker-compose ps redis`
2. 检查 Redis URL 配置
3. 查看 Redis 日志: `docker-compose logs redis`

## 扩展部署

### 添加新服务

在 `docker-compose.yml` 中添加新服务定义。

### 自定义配置

修改 `docker-compose.yml` 中的环境变量和卷挂载。

### 多环境部署

使用不同的 Compose 文件：
- `docker-compose.yml` - 生产环境
- `docker-compose.dev.yml` - 开发环境
- `docker-compose.staging.yml` - 预发布环境（可自定义）

