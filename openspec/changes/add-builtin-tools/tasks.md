## 1. 实现文件读取工具 (read_tool)

- [ ] 1.1 创建 `codebase_driven_agent/tools/read_tool.py`
- [ ] 1.2 实现 `ReadToolInput` 模型（file_path, offset, limit）
- [ ] 1.3 实现 `ReadTool` 类，继承 `BaseCodebaseTool`
- [ ] 1.4 实现文件读取逻辑（支持行号范围、二进制文件检测）
- [ ] 1.5 实现错误处理（文件不存在、权限错误等）
- [ ] 1.6 添加单元测试

## 2. 实现文件匹配工具 (glob_tool)

- [ ] 2.1 创建 `codebase_driven_agent/tools/glob_tool.py`
- [ ] 2.2 实现 `GlobToolInput` 模型（pattern, path）
- [ ] 2.3 实现 `GlobTool` 类，使用 Python `glob` 或 `pathlib`
- [ ] 2.4 实现文件匹配逻辑（支持递归、排序）
- [ ] 2.5 添加结果截断和排序（按修改时间）
- [ ] 2.6 添加单元测试

## 3. 实现内容搜索工具 (grep_tool)

- [ ] 3.1 创建 `codebase_driven_agent/tools/grep_tool.py`
- [ ] 3.2 实现 `GrepToolInput` 模型（pattern, path, include）
- [ ] 3.3 实现 `GrepTool` 类，使用 `ripgrepy` 或 Python `re`
- [ ] 3.4 实现正则表达式搜索逻辑
- [ ] 3.5 实现文件过滤（include 参数）
- [ ] 3.6 添加结果格式化和排序
- [ ] 3.7 添加单元测试

## 4. 实现命令执行工具 (bash_tool)

- [ ] 4.1 创建 `codebase_driven_agent/tools/bash_tool.py`
- [ ] 4.2 实现 `BashToolInput` 模型（command, cwd）
- [ ] 4.3 实现 `BashTool` 类，使用 `subprocess`
- [ ] 4.4 实现命令执行逻辑（超时、输出截断）
- [ ] 4.5 实现安全限制（禁止危险命令）
- [ ] 4.6 添加单元测试

## 5. 实现网络搜索工具 (websearch_tool) - 可选

- [ ] 5.1 创建 `codebase_driven_agent/tools/websearch_tool.py`
- [ ] 5.2 实现 `WebSearchToolInput` 模型（query, max_results）
- [ ] 5.3 实现 `WebSearchTool` 类，集成搜索 API（如 Exa、Serper）
- [ ] 5.4 实现搜索结果格式化
- [ ] 5.5 添加配置检查（API Key）
- [ ] 5.6 添加单元测试

## 6. 实现网页获取工具 (webfetch_tool) - 可选

- [ ] 6.1 创建 `codebase_driven_agent/tools/webfetch_tool.py`
- [ ] 6.2 实现 `WebFetchToolInput` 模型（url）
- [ ] 6.3 实现 `WebFetchTool` 类，使用 `requests` 或 `httpx`
- [ ] 6.4 实现网页内容提取（HTML 解析、文本提取）
- [ ] 6.5 实现超时和错误处理
- [ ] 6.6 添加单元测试

## 7. 注册所有新工具

- [ ] 7.1 更新 `codebase_driven_agent/tools/registry.py` 的 `_register_default_tools`
- [ ] 7.2 确保所有工具正确注册到 `ToolRegistry`
- [ ] 7.3 验证工具列表 API 返回新工具

## 8. 更新文档

- [ ] 8.1 更新 `docs/EXTENDING.md`，添加新工具示例
- [ ] 8.2 更新 `README.md`，说明新工具功能
- [ ] 8.3 创建 `docs/BUILTIN_TOOLS.md`，详细说明每个工具的用法

## 9. 集成测试

- [ ] 9.1 测试 Agent 能够正确调用新工具
- [ ] 9.2 测试工具的错误处理
- [ ] 9.3 测试工具的并发使用
- [ ] 9.4 验证工具描述对 LLM 的指导作用
