# AST 代码分析功能设置指南

## 概述

本项目已集成 tree-sitter 用于 AST（抽象语法树）代码分析，提供更精确的代码搜索和分析能力。

## 依赖管理

### 已更新的依赖文件

1. **requirements.txt**
   - 已添加 tree-sitter 核心库和相关语言解析器
   - 位置：项目根目录 `requirements.txt`

2. **pyproject.toml**
   - 已添加 tree-sitter 依赖到 `dependencies` 列表
   - 位置：项目根目录 `pyproject.toml`

### 依赖列表

```txt
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0
tree-sitter-javascript>=0.21.0
tree-sitter-typescript>=0.21.0
tree-sitter-cpp>=0.21.0
tree-sitter-java>=0.21.0
```

## 安装步骤

### 方法 1: 使用 requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

### 方法 2: 使用 pyproject.toml

```bash
pip install -e .
```

### 方法 3: 单独安装 AST 依赖

```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-cpp tree-sitter-java
```

## 验证安装

运行测试脚本验证安装：

```bash
python scripts/test_ast_simple.py
```

如果安装成功，应该看到：
- ✅ tree-sitter 核心库已安装
- ✅ python 语言解析器已安装
- ✅ javascript 语言解析器已安装
- ✅ typescript 语言解析器已安装
- AST 解析功能测试通过

## 功能说明

### 已实现的功能

1. **AST 解析器配置模块** (`codebase_driven_agent/tools/ast_parser.py`)
   - 支持 Python、JavaScript、TypeScript、C++、Java
   - 自动语言检测
   - 解析器初始化和管理

2. **AST 代码分析器** (`codebase_driven_agent/tools/ast_analyzer.py`)
   - `find_function_definition()` - 查找函数定义
   - `find_function_calls()` - 查找函数调用
   - `trace_call_chain()` - 追踪调用链
   - `find_variable_usage()` - 查找变量使用

3. **CodeTool 集成** (`codebase_driven_agent/tools/code_tool.py`)
   - 自动检测 AST 可用性
   - 多策略搜索（AST → ripgrep → 文件搜索）
   - 自动回退机制

### 使用方式

AST 功能会自动启用（如果已安装依赖）。在 CodeTool 中搜索代码时：

- **函数搜索**：优先使用 AST 精确查找函数定义和调用
- **变量搜索**：使用 AST 精确查找变量使用位置
- **自动回退**：如果 AST 不可用，自动使用 ripgrep 文本搜索

## 新环境部署

在新环境中部署时，确保：

1. **安装所有依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **验证安装**
   ```bash
   python scripts/test_ast_simple.py
   ```

3. **检查日志**
   启动应用后，查看日志确认 AST 解析器初始化成功：
   ```
   INFO: Loaded tree-sitter Python language parser
   INFO: Loaded tree-sitter JavaScript language parser
   INFO: Loaded tree-sitter TypeScript language parser
   INFO: Loaded tree-sitter C++ language parser
   INFO: Loaded tree-sitter Java language parser
   INFO: AST parser initialized with 5 language(s)
   ```

## 故障排除

### 问题：ModuleNotFoundError: No module named 'tree_sitter'

**解决方案**：
```bash
pip install tree-sitter
```

### 问题：语言解析器未安装警告

**解决方案**：
```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-cpp tree-sitter-java
```

### 问题：AST 功能未启用

**检查**：
1. 确认依赖已安装
2. 查看应用日志，确认 AST 解析器初始化成功
3. 如果 AST 不可用，CodeTool 会自动回退到 ripgrep 搜索

## 注意事项

- AST 功能是**可选的**，如果未安装 tree-sitter，系统会自动使用文本搜索（ripgrep）
- AST 搜索更精确，但可能比文本搜索稍慢
- 当前支持的语言：Python、JavaScript、TypeScript、C++、Java
- 未来可扩展支持更多语言（Go、Rust、C# 等）

## 相关文件

- `codebase_driven_agent/tools/ast_parser.py` - AST 解析器配置
- `codebase_driven_agent/tools/ast_analyzer.py` - AST 代码分析器
- `codebase_driven_agent/tools/code_tool.py` - CodeTool（已集成 AST）
- `scripts/test_ast_simple.py` - 简单测试脚本
- `scripts/test_ast_parser.py` - 完整测试脚本（需要项目依赖）
