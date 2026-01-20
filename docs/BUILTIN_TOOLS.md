# 内置工具集文档

本文档详细说明 Codebase Driven Agent 平台提供的所有内置工具及其使用方法。

## 工具概览

| 工具名称 | 功能 | 状态 |
|---------|------|------|
| `read` | 读取文件内容 | ✅ 已启用 |
| `glob` | 文件模式匹配 | ✅ 已启用 |
| `grep` | 正则表达式搜索 | ✅ 已启用 |
| `bash` | 执行 shell 命令 | ✅ 已启用 |
| `webfetch` | 获取网页内容 | ✅ 已启用 |
| `websearch` | 网络搜索 | ⚠️ 需要 API Key |

## 1. read - 文件读取工具

### 功能描述

读取代码仓库中的文件内容，支持指定行号范围。

### 使用场景

- 查看特定文件的代码内容
- 查看配置文件
- 查看文档文件
- 查看特定行号的代码片段

### 参数说明

- `file_path` (必需): 文件路径，相对于代码仓库根目录
- `offset` (可选): 起始行号（从1开始，包含该行）。如果不指定，从文件开头读取
- `limit` (可选): 读取的行数。如果不指定，读取到文件末尾

### 使用示例

```python
# 读取整个文件
read(file_path="src/main.py")

# 读取文件的第 10-20 行
read(file_path="src/main.py", offset=10, limit=11)

# 读取文件的前 50 行
read(file_path="src/main.py", limit=50)
```

### 返回格式

```
文件: src/main.py
总行数: 150
显示范围: 第 10 行 - 第 20 行（共 11 行）

内容:

  10 | def main():
  11 |     print("Hello, World!")
  12 |     ...
```

### 注意事项

- 二进制文件会被自动检测并拒绝读取
- 文件路径必须在代码仓库范围内（防止路径遍历攻击）
- 大文件会自动截断输出

---

## 2. glob - 文件匹配工具

### 功能描述

使用 glob 模式匹配文件，支持递归搜索。

### 使用场景

- 查找特定类型的文件（如所有 Python 文件）
- 查找特定目录下的文件
- 查找配置文件
- 批量文件操作前的文件发现

### 参数说明

- `pattern` (必需): glob 模式（如 `*.py`、`**/*.ts`、`src/**/*.js`）
- `path` (可选): 搜索的基础路径，相对于代码仓库根目录。如果不指定，从代码仓库根目录搜索

### 使用示例

```python
# 查找所有 Python 文件
glob(pattern="*.py")

# 递归查找所有 TypeScript 文件
glob(pattern="**/*.ts")

# 在 src 目录下查找所有 JavaScript 文件
glob(pattern="**/*.js", path="src")

# 查找配置文件
glob(pattern="**/*.json")
glob(pattern="**/*.yaml")
```

### 返回格式

```
模式: *.py
匹配文件数: 25

文件列表:

  1. src/main.py
  2. src/utils.py
  3. tests/test_main.py
  ...
```

### 注意事项

- 结果按修改时间排序（最新的在前）
- 最多返回 100 个文件（避免结果过多）
- 只返回文件，不返回目录

---

## 3. grep - 内容搜索工具

### 功能描述

使用正则表达式搜索文件内容，支持文件类型过滤。

### 使用场景

- 查找函数调用
- 查找变量使用
- 查找错误信息
- 查找特定字符串或模式

### 参数说明

- `pattern` (必需): 正则表达式模式
- `path` (可选): 搜索路径（文件或目录），相对于代码仓库根目录。如果不指定，搜索整个代码仓库
- `include` (可选): 文件类型过滤（glob 模式，如 `*.py`、`*.js`）。如果不指定，搜索所有文本文件

### 使用示例

```python
# 搜索所有包含 "def main" 的文件
grep(pattern="def main")

# 在 Python 文件中搜索特定函数调用
grep(pattern="print\(", include="*.py")

# 在特定目录下搜索
grep(pattern="error", path="src")

# 搜索错误信息
grep(pattern="Error|Exception", include="*.py")
```

### 返回格式

```
搜索模式: def main
匹配数: 5

匹配结果:

文件: src/main.py
   10 | def main():
   15 |     main()

文件: tests/test_main.py
    5 | def test_main():
```

### 注意事项

- 优先使用 ripgrep（如果可用），否则使用 Python regex
- 结果按文件和行号排序
- 最多返回 50 个匹配结果
- 自动跳过二进制文件

---

## 4. bash - 命令执行工具

### 功能描述

执行 shell 命令，支持安全限制。

### 使用场景

- 检查文件系统状态
- 运行构建命令
- 查看系统信息
- 执行 Git 操作

### 参数说明

- `command` (必需): 要执行的 shell 命令
- `cwd` (可选): 工作目录，相对于代码仓库根目录。如果不指定，使用代码仓库根目录

### 使用示例

```python
# 列出目录内容
bash(command="ls -la")

# 检查 Git 状态
bash(command="git status")

# 查看文件信息
bash(command="file src/main.py")

# 在特定目录执行命令
bash(command="ls", cwd="src")
```

### 安全限制

以下命令和模式被禁止执行：

- **危险命令**: `rm`, `del`, `delete`, `format`, `mkfs`, `dd`
- **系统命令**: `shutdown`, `reboot`, `halt`, `poweroff`
- **权限命令**: `sudo`, `su`, `chmod`, `chown`
- **网络命令**: `wget`, `curl`, `nc`, `netcat`
- **代码执行**: `python`, `python3`, `node`, `ruby`
- **Shell 内置**: `eval`, `exec`, `source`
- **危险模式**: `rm -rf`, `> /dev/`, `| sh`, `| bash`, 命令替换等

### 返回格式

```
命令: git status
退出码: 0

标准输出:
On branch main
Changes not staged for commit:
  modified:   src/main.py
```

### 注意事项

- 命令执行超时时间为 30 秒
- 输出会自动截断（避免过长输出）
- 退出码不为 0 时，工具返回失败状态

---

## 5. webfetch - 网页获取工具

### 功能描述

获取网页内容并提取文本。

### 使用场景

- 获取文档
- 获取 API 文档
- 获取错误信息参考
- 获取最佳实践

### 参数说明

- `url` (必需): 网页 URL（必须以 `http://` 或 `https://` 开头）

### 使用示例

```python
# 获取网页内容
webfetch(url="https://docs.python.org/3/library/os.html")

# 获取 API 文档
webfetch(url="https://api.example.com/docs")
```

### 返回格式

```
URL: https://docs.python.org/3/library/os.html
内容类型: text/html
内容长度: 5000 字符

内容:

Python Documentation
...
```

### 注意事项

- 请求超时时间为 10 秒
- 最大内容长度为 1MB
- 自动提取 HTML 文本（移除 script、style 标签）
- 需要安装 `httpx` 或 `requests` 库
- 可选安装 `beautifulsoup4` 以获得更好的 HTML 解析效果

---

## 6. websearch - 网络搜索工具（可选）

### 功能描述

在网络上搜索信息。需要配置搜索 API Key。

### 使用场景

- 查找错误解决方案
- 查找 API 文档
- 查找最佳实践
- 查找代码示例

### 参数说明

- `query` (必需): 搜索查询
- `max_results` (可选): 最大结果数量（默认 5，最大 10）

### 配置要求

需要配置以下环境变量之一：

- `EXA_API_KEY`: Exa API Key
- `SERPER_API_KEY`: Serper API Key

### 使用示例

```python
# 搜索错误解决方案
websearch(query="Python TypeError: 'NoneType' object is not callable")

# 搜索 API 文档
websearch(query="FastAPI query parameters documentation")

# 限制结果数量
websearch(query="Python best practices", max_results=3)
```

### 返回格式

```
搜索查询: Python TypeError
结果数: 5

1. Python TypeError Explained
   URL: https://example.com/python-typeerror
   摘要: TypeError occurs when...

2. Common Python Errors
   URL: https://example.com/python-errors
   摘要: ...
```

### 注意事项

- 需要配置搜索 API Key 才能使用
- 优先使用 Exa API，如果没有则使用 Serper API
- 结果数量限制在 1-10 之间
- 需要安装 `httpx` 或 `requests` 库

---

## 工具使用最佳实践

### 1. 组合使用工具

工具可以组合使用，提高效率：

```python
# 1. 先查找文件
files = glob(pattern="**/*error*.py")

# 2. 在找到的文件中搜索
grep(pattern="def.*error", include="*error*.py")

# 3. 读取相关文件
read(file_path="src/error_handler.py", offset=1, limit=50)
```

### 2. 合理使用文件过滤

使用 `include` 参数可以大幅提高搜索效率：

```python
# 只在 Python 文件中搜索
grep(pattern="import", include="*.py")

# 只在配置文件中搜索
glob(pattern="*.json")
grep(pattern="database", include="*.json")
```

### 3. 使用行号范围

对于大文件，使用 `offset` 和 `limit` 参数：

```python
# 只读取关键部分
read(file_path="src/main.py", offset=100, limit=50)
```

### 4. 安全使用 bash 命令

避免执行危险命令，优先使用其他工具：

```python
# ✅ 推荐：使用 glob 查找文件
glob(pattern="*.py")

# ❌ 不推荐：使用 bash 查找文件
bash(command="find . -name '*.py'")
```

---

## 工具注册和启用

所有工具通过 `ToolRegistry` 自动注册。可以通过 API 管理工具：

```bash
# 列出所有工具
GET /api/v1/tools

# 启用工具
POST /api/v1/tools/{tool_name}/enable

# 禁用工具
POST /api/v1/tools/{tool_name}/disable
```

---

## 故障排查

### 工具未出现在列表中

1. 检查工具是否正确注册到 `ToolRegistry`
2. 检查工具初始化是否成功（查看日志）
3. 检查工具依赖是否安装

### 工具执行失败

1. 检查参数是否正确
2. 检查代码仓库路径是否配置（`CODE_REPO_PATH`）
3. 检查文件权限和路径
4. 查看日志获取详细错误信息

### websearch 工具不可用

1. 检查是否配置了 `EXA_API_KEY` 或 `SERPER_API_KEY`
2. 检查 API Key 是否有效
3. 检查网络连接

---

## 扩展工具

如果需要添加自定义工具，请参考 [EXTENDING.md](EXTENDING.md) 中的工具扩展指南。
