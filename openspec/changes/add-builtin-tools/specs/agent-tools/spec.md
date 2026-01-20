## ADDED Requirements

### Requirement: 文件读取工具
Agent SHALL 能够读取代码库中的文件内容，支持指定行号范围以减少上下文。

#### Scenario: 读取完整文件
- **WHEN** Agent 需要查看文件内容
- **THEN** 使用 `read_tool` 读取文件，返回文件内容（默认最多 2000 行）

#### Scenario: 读取指定行范围
- **WHEN** Agent 需要查看文件的特定行（如第 10-50 行）
- **THEN** 使用 `read_tool` 的 `offset` 和 `limit` 参数，只返回指定范围的内容

#### Scenario: 文件不存在处理
- **WHEN** Agent 尝试读取不存在的文件
- **THEN** 返回清晰的错误信息，建议可能的文件路径

### Requirement: 文件模式匹配工具
Agent SHALL 能够使用 glob 模式快速查找匹配的文件。

#### Scenario: 查找特定扩展名文件
- **WHEN** Agent 需要查找所有 `.py` 文件
- **THEN** 使用 `glob_tool` 的 `pattern: "**/*.py"`，返回匹配的文件路径列表

#### Scenario: 递归搜索目录
- **WHEN** Agent 需要在特定目录下递归搜索文件
- **THEN** 使用 `glob_tool` 的 `path` 参数指定搜索目录，`pattern` 使用 `**/*` 进行递归匹配

#### Scenario: 结果排序
- **WHEN** `glob_tool` 返回多个文件
- **THEN** 结果按文件修改时间降序排列（最新修改的文件在前）

### Requirement: 内容搜索工具
Agent SHALL 能够使用正则表达式在代码库中搜索匹配的内容。

#### Scenario: 搜索函数定义
- **WHEN** Agent 需要查找函数定义（如 `def function_name`）
- **THEN** 使用 `grep_tool` 的 `pattern: "def function_name"`，返回匹配的文件路径和行号

#### Scenario: 限制搜索范围
- **WHEN** Agent 只在特定文件类型中搜索（如只搜索 `.py` 文件）
- **THEN** 使用 `grep_tool` 的 `include: "*.py"` 参数过滤文件

#### Scenario: 结果格式化
- **WHEN** `grep_tool` 找到多个匹配
- **THEN** 返回格式为 `文件路径:行号: 匹配内容`，按文件修改时间排序

### Requirement: 命令执行工具
Agent SHALL 能够执行 shell 命令以完成复杂任务。

#### Scenario: 执行简单命令
- **WHEN** Agent 需要执行命令（如 `ls -la`）
- **THEN** 使用 `bash_tool` 执行命令，返回标准输出和错误输出

#### Scenario: 命令超时处理
- **WHEN** 命令执行时间过长
- **THEN** `bash_tool` 在超时后终止命令并返回超时错误

#### Scenario: 安全限制
- **WHEN** Agent 尝试执行危险命令（如 `rm -rf /`）
- **THEN** `bash_tool` 拒绝执行并返回安全错误

### Requirement: 网络搜索工具（可选）
Agent SHALL 能够进行网络搜索以获取外部信息（需要配置 API Key）。

#### Scenario: 搜索技术文档
- **WHEN** Agent 需要查找技术文档或 API 信息
- **THEN** 使用 `websearch_tool` 搜索关键词，返回相关链接和摘要

#### Scenario: API Key 检查
- **WHEN** `websearch_tool` 未配置 API Key
- **THEN** 工具返回配置错误，提示需要设置 API Key

### Requirement: 网页获取工具（可选）
Agent SHALL 能够获取网页内容以分析外部资源。

#### Scenario: 获取网页内容
- **WHEN** Agent 需要查看网页内容
- **THEN** 使用 `webfetch_tool` 获取 URL 内容，返回提取的文本内容

#### Scenario: HTML 解析
- **WHEN** `webfetch_tool` 获取 HTML 页面
- **THEN** 自动提取文本内容，去除 HTML 标签，返回可读的文本

#### Scenario: 超时和错误处理
- **WHEN** 网页获取失败或超时
- **THEN** 返回清晰的错误信息，说明失败原因

### Requirement: 工具注册和管理
所有新工具 SHALL 通过 `ToolRegistry` 统一注册和管理。

#### Scenario: 工具自动注册
- **WHEN** 系统启动
- **THEN** 所有内置工具自动注册到 `ToolRegistry`，默认启用

#### Scenario: 工具动态启用/禁用
- **WHEN** 管理员通过 API 禁用某个工具
- **THEN** Agent 无法调用该工具，但其他工具正常工作

#### Scenario: 工具列表查询
- **WHEN** 用户查询可用工具列表
- **THEN** API 返回所有已注册工具的信息（名称、描述、状态）
