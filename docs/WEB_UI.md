# Web UI 启动指南

本文档说明如何启动和使用 Codebase Driven Agent 的 Web UI。

## 前置要求

- Node.js 16+ 和 npm（或 yarn、pnpm）
- 后端服务已启动（默认运行在 http://localhost:8000）

## 快速开始

### 1. 进入 Web 目录

```bash
cd web
```

### 2. 安装依赖

```bash
npm install
```

如果使用 yarn：

```bash
yarn install
```

如果使用 pnpm：

```bash
pnpm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

启动后，你会看到类似输出：

```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### 4. 访问 Web UI

打开浏览器访问：**http://localhost:3000**

## 配置

### API 地址配置

Web UI 默认连接到 `http://localhost:8000`。如果需要修改：

**方式 1: 修改 vite.config.ts（开发环境）**

编辑 `web/vite.config.ts`：

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://your-backend-host:8000',  // 修改这里
        changeOrigin: true,
      },
    },
  },
})
```

**方式 2: 使用环境变量（推荐）**

创建 `web/.env` 文件：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

然后在代码中使用：

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
```

### API Key 配置

Web UI 支持在界面中输入 API Key，会自动保存到浏览器的 localStorage。

如果后端配置了 `API_KEY`，在 Web UI 的 API Key 输入框中输入对应的值即可。

## 功能说明

### 主要功能

1. **问题输入**
   - 文本输入框：输入错误日志、问题描述等
   - 文件上传：上传代码文件或日志文件作为上下文

2. **分析模式**
   - **同步模式**：等待分析完成后一次性返回结果
   - **流式模式（SSE）**：实时显示分析进度和结果

3. **结果展示**
   - 根因分析
   - 应急建议
   - 置信度评分
   - 相关代码引用
   - 相关日志引用
   - Agent 思考过程（可折叠）

4. **实时进度**
   - 进度条显示
   - 百分比显示
   - 当前步骤信息

## 开发模式

### 热重载

开发服务器支持热重载，修改代码后会自动刷新浏览器。

### 查看日志

浏览器控制台（F12）会显示：
- API 请求日志
- SSE 连接状态
- 错误信息

## 构建生产版本

### 构建

```bash
npm run build
```

构建产物在 `web/dist/` 目录。

### 预览构建结果

```bash
npm run preview
```

### 部署

将 `web/dist/` 目录的内容部署到静态文件服务器：

**Nginx 配置示例**：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/web/dist;
    index index.html;
    
    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE 支持
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

## 常见问题

### 1. 端口被占用

如果 3000 端口被占用，Vite 会自动尝试其他端口，或手动指定：

```bash
npm run dev -- --port 3001
```

### 2. 无法连接到后端

**检查项**：
- 后端服务是否已启动（http://localhost:8000）
- 后端健康检查是否正常：`curl http://localhost:8000/health`
- 检查 `vite.config.ts` 中的 proxy 配置
- 检查浏览器控制台的错误信息

### 3. SSE 连接失败

**检查项**：
- 后端是否支持 SSE（检查 `/api/v1/analyze/stream` 端点）
- 浏览器是否支持 EventSource API
- 检查网络代理设置（某些代理可能不支持 SSE）

### 4. API Key 认证失败

**检查项**：
- 后端是否配置了 `API_KEY`
- Web UI 中输入的 API Key 是否正确
- 检查浏览器控制台的错误信息

### 5. CORS 错误

如果直接访问后端 API（不使用代理），可能遇到 CORS 错误。

**解决方案**：
- 使用 Vite 的代理功能（推荐）
- 或配置后端 CORS 允许前端域名

## 开发技巧

### 查看网络请求

1. 打开浏览器开发者工具（F12）
2. 切换到 "Network" 标签
3. 执行分析操作
4. 查看 API 请求和响应

### 调试 SSE 连接

1. 打开浏览器开发者工具（F12）
2. 切换到 "Network" 标签
3. 筛选 "EventStream" 类型
4. 查看 SSE 消息流

### 测试不同场景

- **同步模式**：适合快速测试，结果一次性返回
- **流式模式**：适合长时间分析，可以看到实时进度

## 下一步

- 查看 [API 文档](API.md) 了解后端 API 接口
- 查看 [使用指南](USAGE.md) 了解使用场景
- 查看 [配置说明](CONFIG.md) 了解详细配置

