# Codebase Driven Agent Web UI

Codebase Driven Agent 的 Web 用户界面。

## 技术栈

- React 18
- TypeScript
- Vite
- React Markdown（用于渲染 Markdown 内容）

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 预览构建结果

```bash
npm run preview
```

### 运行测试

```bash
# 运行测试
npm test

# 运行测试（UI 模式）
npm run test:ui

# 运行测试（覆盖率）
npm run test:coverage
```

## 功能

- ✅ 用户输入界面（文本输入、文件上传）
- ✅ 分析结果展示（根因分析、建议、置信度）
- ✅ 相关代码和日志展示
- ✅ Agent 思考过程折叠显示（预留）
- ✅ SSE 流式数据接收
- ✅ 实时进度展示（进度条、百分比、步骤信息）
- ✅ 流式/同步接口切换

## 配置

### API 地址

默认代理到 `http://localhost:8000`，可在 `vite.config.ts` 中修改。

### API Key

在界面中输入 API Key，会自动保存到 localStorage。

## 部署

构建后的静态文件可以部署到任何静态文件服务器（如 Nginx、Apache）。

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/web/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

