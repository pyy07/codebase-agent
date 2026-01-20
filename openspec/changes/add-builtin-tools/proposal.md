# Change: 添加内置工具集

## Why

参考 TypeScript 实现的工具系统（`codebase_driven_agent/open_tool/`），当前 Python 代码库的工具集相对有限。为了提升 Agent 的执行能力，需要添加更多实用的内置工具，包括：

1. **文件操作工具**：`read`（读取文件）、`glob`（文件模式匹配）
2. **内容搜索工具**：`grep`（正则表达式搜索）
3. **命令执行工具**：`bash`（执行 shell 命令）
4. **网络工具**：`websearch`（网络搜索）、`webfetch`（获取网页内容）

这些工具将显著增强 Agent 的代码库探索、问题分析和信息获取能力。

## What Changes

- **新增工具**：
  - `read_tool` - 读取文件内容（支持行号范围）
  - `glob_tool` - 使用 glob 模式匹配文件
  - `grep_tool` - 使用正则表达式搜索文件内容
  - `bash_tool` - 执行 shell 命令
  - `websearch_tool` - 网络搜索（可选，需要 API Key）
  - `webfetch_tool` - 获取网页内容

- **工具注册**：所有新工具通过 `ToolRegistry` 注册，支持动态启用/禁用

- **工具描述**：为每个工具提供详细的中文描述，帮助 LLM 理解何时使用

- **错误处理**：统一的错误处理和结果格式化

## Impact

- **受影响的规范**：`agent-tools` capability（新增）
- **受影响的代码**：
  - `codebase_driven_agent/tools/` - 新增工具实现
  - `codebase_driven_agent/tools/registry.py` - 注册新工具
  - `codebase_driven_agent/agent/graph_executor.py` - 可能需要更新工具映射逻辑
  - `docs/EXTENDING.md` - 更新扩展文档

- **向后兼容性**：完全兼容，不影响现有工具
