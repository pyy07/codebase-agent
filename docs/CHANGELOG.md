# 更新日志

## 2024-01-XX - 配置和功能改进

### 新增功能

1. **支持自定义 LLM Base URL**
   - 添加了 `OPENAI_BASE_URL` 配置项，支持使用其他 OpenAI 兼容的 API
   - 添加了 `LLM_BASE_URL` 和 `LLM_API_KEY` 通用配置，支持任意供应商的大模型
   - 更新了 `create_llm()` 函数，优先使用自定义 Base URL

2. **LOGYI_APPNAME 可选配置**
   - `LOGYI_APPNAME` 不再是必需配置
   - 当未配置且用户未提供时，Agent 会自动询问用户项目名称
   - 更新了 `LogTool` 的错误提示，引导 Agent 询问用户

3. **修复 .env.example 文件**
   - 重新创建了 `.env.example` 文件，清除乱码
   - 添加了完整的配置说明和示例
   - 使用 UTF-8 编码确保正确显示

### 配置变更

#### 新增配置项

```bash
# LLM 自定义 Base URL
OPENAI_BASE_URL=https://your-custom-api-endpoint.com/v1
LLM_BASE_URL=https://your-custom-api-endpoint.com/v1
LLM_API_KEY=your-api-key
LLM_PROVIDER=openai  # openai, anthropic, custom
```

#### 配置项说明变更

- `LOGYI_APPNAME`: 从"必需"改为"可选"
  - 如果未配置，Agent 会在需要时询问用户
  - 如果配置了，会作为默认值使用

### 代码变更

1. **config.py**
   - 添加了 `openai_base_url`、`llm_base_url`、`llm_api_key`、`llm_provider` 配置项

2. **agent/executor.py**
   - 更新了 `create_llm()` 函数，支持自定义 Base URL
   - 优先使用 `LLM_BASE_URL` + `LLM_API_KEY` 配置
   - 其次使用 `OPENAI_BASE_URL` + `OPENAI_API_KEY` 配置

3. **tools/log_tool.py**
   - 更新了错误提示，当缺少 appname 时，提示 Agent 询问用户
   - 更新了工具描述，说明 appname 参数的使用方式

4. **agent/prompt.py**
   - 添加了日志查询特殊说明，指导 Agent 在没有 appname 时询问用户

### 文档更新

1. **docs/CONFIG.md**
   - 添加了自定义 Base URL 配置说明
   - 更新了 LOGYI_APPNAME 说明（从必需改为可选）

2. **docs/LOCAL_TESTING.md**
   - 添加了自定义 Base URL 配置示例
   - 更新了 LOGYI_APPNAME 说明

3. **README.md**
   - 更新了配置示例，包含自定义 Base URL 和可选的 LOGYI_APPNAME

4. **docker-compose.yml**
   - 添加了新的 LLM 配置环境变量

### 使用示例

#### 使用其他供应商的大模型

```bash
# 方式 1: 使用 OPENAI_BASE_URL（推荐）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.your-provider.com/v1
LLM_MODEL=your-model-name

# 方式 2: 使用通用配置
LLM_BASE_URL=https://api.your-provider.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

#### LOGYI_APPNAME 可选配置

```bash
# 可以不配置 LOGYI_APPNAME
LOGYI_BASE_URL=https://logyi.example.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-api-key
# LOGYI_APPNAME 不配置，Agent 会在需要时询问用户

# 或者配置默认值
LOGYI_APPNAME=your-default-project
```

### 向后兼容性

- 所有变更都是向后兼容的
- 现有的配置仍然有效
- 如果不使用新功能，无需修改配置

