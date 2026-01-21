## 1. 实现文件读取工具 (read_tool)

- [x] 1.1 创建 `codebase_driven_agent/tools/read_tool.py`
- [x] 1.2 实现 `ReadToolInput` 模型（file_path, offset, limit）
- [x] 1.3 实现 `ReadTool` 类，继承 `BaseCodebaseTool`
- [x] 1.4 实现文件读取逻辑（支持行号范围、二进制文件检测）
- [x] 1.5 实现错误处理（文件不存在、权限错误等）
- [x] 1.6 添加单元测试

## 2. 实现文件匹配工具 (glob_tool)

- [x] 2.1 创建 `codebase_driven_agent/tools/glob_tool.py`
- [x] 2.2 实现 `GlobToolInput` 模型（pattern, path）
- [x] 2.3 实现 `GlobTool` 类，使用 Python `glob` 或 `pathlib`
- [x] 2.4 实现文件匹配逻辑（支持递归、排序）
- [x] 2.5 添加结果截断和排序（按修改时间）
- [x] 2.6 添加单元测试

## 3. 实现内容搜索工具 (grep_tool)

- [x] 3.1 创建 `codebase_driven_agent/tools/grep_tool.py`
- [x] 3.2 实现 `GrepToolInput` 模型（pattern, path, include）
- [x] 3.3 实现 `GrepTool` 类，使用 `ripgrepy` 或 Python `re`
- [x] 3.4 实现正则表达式搜索逻辑
- [x] 3.5 实现文件过滤（include 参数）
- [x] 3.6 添加结果格式化和排序
- [x] 3.7 添加单元测试

## 4. 实现命令执行工具 (bash_tool)

- [x] 4.1 创建 `codebase_driven_agent/tools/bash_tool.py`
- [x] 4.2 实现 `BashToolInput` 模型（command, cwd）
- [x] 4.3 实现 `BashTool` 类，使用 `subprocess`
- [x] 4.4 实现命令执行逻辑（超时、输出截断）
- [x] 4.5 实现安全限制（禁止危险命令）
- [x] 4.6 添加单元测试

## 5. 实现网络搜索工具 (websearch_tool) - 可选

- [x] 5.1 创建 `codebase_driven_agent/tools/websearch_tool.py`
- [x] 5.2 实现 `WebSearchToolInput` 模型（query, max_results）
- [x] 5.3 实现 `WebSearchTool` 类，集成搜索 API（如 Exa、Serper）
- [x] 5.4 实现搜索结果格式化
- [x] 5.5 添加配置检查（API Key）
- [x] 5.6 添加单元测试

## 6. 实现网页获取工具 (webfetch_tool) - 可选

- [x] 6.1 创建 `codebase_driven_agent/tools/webfetch_tool.py`
- [x] 6.2 实现 `WebFetchToolInput` 模型（url）
- [x] 6.3 实现 `WebFetchTool` 类，使用 `requests` 或 `httpx`
- [x] 6.4 实现网页内容提取（HTML 解析、文本提取）
- [x] 6.5 实现超时和错误处理
- [x] 6.6 添加单元测试

## 7. 注册所有新工具

- [x] 7.1 更新 `codebase_driven_agent/tools/registry.py` 的 `_register_default_tools`
- [x] 7.2 确保所有工具正确注册到 `ToolRegistry`
- [x] 7.3 验证工具列表 API 返回新工具 - `/api/v1/tools` 接口已存在，返回所有注册的工具

## 8. 更新文档

- [x] 8.1 更新 `docs/EXTENDING.md`，添加新工具示例
- [x] 8.2 更新 `README.md`，说明新工具功能
- [x] 8.3 创建 `docs/BUILTIN_TOOLS.md`，详细说明每个工具的用法

## 9. 集成测试

- [x] 9.1 测试 Agent 能够正确调用新工具 - 已创建集成测试文件 `tests/test_builtin_tools_integration.py`
- [x] 9.2 测试工具的错误处理 - 已测试文件不存在、路径遍历等错误情况
- [x] 9.3 测试工具的并发使用 - 已测试多线程并发访问工具
- [x] 9.4 验证工具描述对 LLM 的指导作用 - 所有工具都有详细的中文描述，已通过工具注册验证
