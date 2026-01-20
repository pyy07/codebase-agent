# AST 代码搜索功能说明

## 概述

`code_search` 工具现在支持使用 AST（抽象语法树）进行代码搜索，可以理解代码结构，查找函数定义、调用关系等。

## 当前状态

- ✅ **已实现**：改进的 ripgrep 多策略搜索（字面量、正则、大小写不敏感等）
- 🚧 **待实现**：AST 搜索功能（框架已搭建，需要安装 tree-sitter）

## 改进的 Ripgrep 搜索

### 多策略搜索

现在 `code_search` 会自动尝试多种搜索策略，按优先级：

1. **字面量搜索（-F）**：精确匹配字符串，适合包含特殊字符的查询
   - 例如：`"no targetStrategy tag when determinePerf"` 会先尝试字面量搜索
   
2. **大小写不敏感搜索（-i）**：忽略大小写差异
   - 例如：`"determinePerf"` 会匹配 `determinePerf`、`DeterminePerf`、`DETERMINEPERF`
   
3. **正则表达式搜索**：支持模式匹配
   - 例如：`"determine.*Perf"` 会匹配 `determinePerf`、`determineStrategyPerf` 等
   
4. **单词边界搜索**：匹配完整单词
   - 例如：`\bdeterminePerf\b` 不会匹配 `determinePerfStrategy`

### 特殊字符处理

如果查询包含正则表达式特殊字符（`()[]{}.*+?^$|\`），会自动：
- 优先尝试转义后的字面量搜索
- 然后尝试正则表达式搜索

## AST 搜索（待实现）

### 安装 tree-sitter

```bash
# 安装 tree-sitter 核心库
pip install tree-sitter

# 安装语言解析器（根据需要选择）
pip install tree-sitter-python      # Python
pip install tree-sitter-cpp         # C/C++
pip install tree-sitter-java        # Java
pip install tree-sitter-javascript  # JavaScript/TypeScript
pip install tree-sitter-go          # Go
pip install tree-sitter-rust        # Rust
```

### 功能规划

AST 搜索将支持：

1. **函数定义查找**
   - 根据函数名查找定义位置
   - 支持跨文件搜索

2. **函数调用关系**
   - 查找某个函数的所有调用位置
   - 查找某个函数调用的所有函数

3. **代码结构理解**
   - 理解类、方法、变量的关系
   - 支持继承、接口实现等

4. **语义搜索**
   - 即使代码重构后，也能找到等价的结构
   - 例如：函数名改变但功能相同

### 实现计划

1. 检测文件语言类型（根据扩展名）
2. 加载对应的 tree-sitter 语言解析器
3. 解析代码为 AST
4. 在 AST 中搜索目标节点
5. 返回匹配的代码位置和上下文

## 使用示例

### 改进后的搜索

```python
# 查询包含特殊字符的字符串
code_search(query="no targetStrategy tag when determinePerf")
# 会自动尝试：
# 1. 字面量搜索（-F）
# 2. 大小写不敏感字面量搜索
# 3. 正则表达式搜索
# 4. AST 搜索（如果可用）
# 5. 文件搜索（回退）
```

### 搜索策略日志

搜索时会记录使用的策略：

```
INFO: Trying ripgrep search with multiple strategies...
DEBUG: Trying ripgrep strategy: literal_escaped with query: no targetStrategy tag when determinePerf
INFO: Ripgrep search succeeded with strategy: literal_fixed_case, found 1 results
```

## 故障排除

### ripgrep 找不到结果

1. **检查查询字符串**：确保没有拼写错误
2. **查看日志**：检查使用了哪些搜索策略
3. **尝试简化查询**：使用更短的关键词
4. **检查文件类型**：确保搜索的文件类型没有被忽略

### AST 搜索不可用

1. **检查安装**：确认已安装 `tree-sitter` 和对应的语言解析器
2. **查看日志**：检查是否有错误信息
3. **回退到 ripgrep**：AST 不可用时会自动使用 ripgrep

## 性能考虑

- **ripgrep**：非常快，适合大多数场景
- **AST 搜索**：较慢，但更准确，适合复杂查询
- **文件搜索**：最慢，仅作为回退方案

## 未来优化

1. **缓存 AST 解析结果**：避免重复解析
2. **增量更新**：只解析变更的文件
3. **并行搜索**：同时使用多种策略
4. **智能策略选择**：根据查询类型选择最佳策略
