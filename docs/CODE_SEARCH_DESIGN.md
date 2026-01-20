# 代码搜索工具设计文档

## 设计理念

`code_search` 工具专注于**代码元素搜索**，而不是通用的文件内容搜索。这使 LLM 能够更精确地定位代码结构，提高搜索效率和准确性。

## 当前设计

### 代码元素搜索类型

1. **函数搜索 (`function`)**
   - 搜索函数定义：`def function_name`, `function function_name`, `fn function_name` 等
   - 搜索函数调用：`function_name(`
   - 支持多种语言：Python, JavaScript, Rust, Go 等

2. **类搜索 (`class`)**
   - 搜索类定义：`class ClassName`, `struct StructName`, `interface InterfaceName`
   - 支持多种语言：Python, JavaScript, TypeScript, Java, C/C++, Rust

3. **变量搜索 (`variable`)**
   - 使用单词边界确保精确匹配
   - 查找变量声明和使用位置

4. **字符串字面量搜索 (`string`)**
   - 搜索代码中的字符串常量
   - 使用字面量搜索策略

5. **文件搜索 (`file`)**
   - 查看文件内容
   - 查看目录结构

6. **自动检测 (`auto`)**
   - 根据查询内容自动推断搜索类型
   - 智能识别文件路径、函数名、类名等

### 搜索策略优先级

1. **AST 搜索**（如果可用且适合）
   - 理解代码结构
   - 精确匹配代码元素
   - 支持跨文件搜索

2. **代码元素搜索**（基于 ripgrep 的模式匹配）
   - 使用正则表达式匹配代码模式
   - 针对不同语言使用不同的模式

3. **通用 ripgrep 搜索**
   - 多策略尝试（字面量、大小写不敏感、正则等）

4. **文件内容搜索**（回退方案）
   - 遍历文件内容进行文本匹配

## 未来扩展方向

### 1. 专门的文件内容搜索工具

创建一个新的 `file_content_search` 工具，专门用于全文搜索：

```python
class FileContentSearchTool(BaseCodebaseTool):
    """文件内容全文搜索工具"""
    name: str = "file_content_search"
    description: str = """
    用于在代码仓库中进行全文搜索，查找包含特定文本的文件。
    
    与 code_search 的区别：
    - code_search: 搜索代码元素（函数、类、变量等）
    - file_content_search: 搜索文件中的任意文本内容
    
    使用场景：
    - 搜索错误信息、日志消息
    - 搜索注释中的关键词
    - 搜索配置值、常量等
    """
```

### 2. 代码结构分析工具

```python
class CodeStructureTool(BaseCodebaseTool):
    """代码结构分析工具"""
    name: str = "code_structure"
    description: str = """
    分析代码结构，提供：
    - 函数调用关系图
    - 类继承关系
    - 模块依赖关系
    - 代码复杂度分析
    """
```

### 3. 代码导航工具

```python
class CodeNavigationTool(BaseCodebaseTool):
    """代码导航工具"""
    name: str = "code_navigation"
    description: str = """
    提供代码导航功能：
    - 跳转到定义（Go to Definition）
    - 查找所有引用（Find All References）
    - 查找调用者（Find Callers）
    - 查找被调用者（Find Callees）
    """
```

### 4. 代码理解工具

```python
class CodeUnderstandingTool(BaseCodebaseTool):
    """代码理解工具"""
    name: str = "code_understanding"
    description: str = """
    使用 AI 理解代码：
    - 解释代码功能
    - 分析代码逻辑
    - 识别代码模式
    - 生成代码文档
    """
```

### 5. AST 增强实现

实现完整的 AST 搜索功能：

```python
def _search_with_ast(self, query: str, search_type: str, max_results: int) -> List[Dict]:
    """使用 AST 进行代码搜索"""
    # 1. 检测文件语言类型
    language = self._detect_language(file_path)
    
    # 2. 加载对应的 tree-sitter 语言解析器
    parser = self._get_parser(language)
    
    # 3. 解析代码为 AST
    tree = parser.parse(code)
    
    # 4. 在 AST 中搜索目标节点
    if search_type == "function":
        nodes = self._find_function_definitions(tree, query)
    elif search_type == "class":
        nodes = self._find_class_definitions(tree, query)
    # ...
    
    # 5. 返回匹配的代码位置和上下文
    return self._format_ast_results(nodes)
```

## 工具使用建议

### 对于 LLM

当需要搜索代码时，应该：

1. **明确搜索目标**：
   - 搜索函数 → 使用 `code_search`，`search_type: "function"`
   - 搜索类 → 使用 `code_search`，`search_type: "class"`
   - 搜索错误信息 → 使用 `file_content_search`（未来）

2. **提供准确的查询字符串**：
   - ✅ 正确：`query: "determinePerf"`, `search_type: "function"`
   - ❌ 错误：`query: "定位 determinePerf 函数"`, `search_type: "auto"`

3. **选择合适的搜索类型**：
   - 如果知道是函数名，明确指定 `search_type: "function"`
   - 如果不确定，使用 `search_type: "auto"` 让系统自动检测

## 迁移指南

### 从旧版本迁移

旧版本的 `code_search` 参数：
```python
{
    "query": "...",
    "max_lines": 100,
    "use_ripgrep": True
}
```

新版本的 `code_search` 参数：
```python
{
    "query": "...",
    "search_type": "auto",  # 新增
    "max_results": 10,      # 替代 max_lines
    "include_context": True
}
```

### 向后兼容

为了保持向后兼容，`_execute` 方法仍然接受旧参数，但会转换为新参数格式。

## 性能考虑

- **AST 搜索**：较慢，但最准确，适合复杂查询
- **代码元素搜索**：中等速度，准确性较高
- **ripgrep 搜索**：非常快，适合大多数场景
- **文件内容搜索**：最慢，仅作为回退方案

## 总结

新的 `code_search` 设计：
- ✅ 专注于代码元素搜索
- ✅ 支持多种搜索类型
- ✅ 智能自动检测
- ✅ 多策略搜索
- ✅ 为未来扩展预留接口

未来可以添加更多专门的工具，形成完整的代码检索工具链。
