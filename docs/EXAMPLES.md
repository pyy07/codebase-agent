# 示例场景

本文档提供了一些常见的问题分析场景示例，帮助理解如何使用 Codebase Driven Agent。

## 场景1：数据库连接错误

### 问题描述

```
错误日志：
2024-01-01 10:00:00 ERROR [main] DatabaseService - Failed to connect to database
java.sql.SQLException: Connection refused
    at com.example.DatabaseService.connect(DatabaseService.java:45)
    at com.example.Application.start(Application.java:20)
```

### Agent 分析流程

1. **解析错误信息**
   - 提取关键词：`DatabaseService`, `connect`, `Connection refused`
   - 识别错误类型：数据库连接失败

2. **代码搜索**
   - 搜索 `DatabaseService` 类
   - 查找 `connect` 方法实现
   - 检查数据库连接配置

3. **日志查询**
   - 查询数据库连接相关的日志
   - 查看连接失败的时间范围
   - 检查是否有其他相关错误

4. **数据库查询**
   - 检查数据库服务状态
   - 验证数据库连接配置

5. **综合分析**
   - 根因：数据库服务未启动或连接配置错误
   - 建议：
     - 检查数据库服务是否运行
     - 验证数据库连接配置（host, port, username, password）
     - 检查网络连接和防火墙设置

## 场景2：API 响应超时

### 问题描述

```
用户反馈：调用 /api/users 接口时，请求超时，没有响应。
时间：2024-01-01 14:00:00 左右
```

### Agent 分析流程

1. **理解问题**
   - 提取关键信息：`/api/users`, `超时`, `14:00:00`

2. **代码搜索**
   - 搜索 `/api/users` 路由处理代码
   - 查找相关的业务逻辑
   - 检查是否有数据库查询或外部 API 调用

3. **日志查询**
   - 查询 14:00:00 左右的日志
   - 查找 `/api/users` 相关的请求日志
   - 检查是否有错误或慢查询日志

4. **数据库查询**
   - 检查用户表的数据量
   - 查看是否有慢查询
   - 检查数据库连接池状态

5. **综合分析**
   - 根因：可能是数据库查询慢、外部 API 调用超时、或代码逻辑问题
   - 建议：
     - 检查数据库查询性能，添加索引
     - 检查外部 API 调用是否正常
     - 添加超时处理和错误日志
     - 考虑添加缓存机制

## 场景3：内存泄漏

### 问题描述

```
系统运行一段时间后，内存使用率持续上升，最终导致 OOM (Out of Memory) 错误。
```

### Agent 分析流程

1. **理解问题**
   - 提取关键信息：`内存泄漏`, `OOM`, `持续上升`

2. **代码搜索**
   - 搜索内存相关的代码
   - 查找集合类（List, Map）的使用
   - 检查资源释放代码（close, dispose）

3. **日志查询**
   - 查询内存相关的日志
   - 查找 OOM 错误日志
   - 检查 JVM 内存使用日志

4. **数据库查询**
   - 检查是否有大量数据查询未释放
   - 查看连接池使用情况

5. **综合分析**
   - 根因：可能是未释放的资源、集合无限增长、或数据库连接泄漏
   - 建议：
     - 检查资源是否正确释放（try-finally, try-with-resources）
     - 检查集合类是否有无限增长的情况
     - 检查数据库连接是否正确关闭
     - 使用内存分析工具（如 jmap, jvisualvm）进行深入分析

## 场景4：代码疑问

### 问题描述

```
这段代码的作用是什么？为什么会出现性能问题？

```python
def process_data(data_list):
    result = []
    for item in data_list:
        processed = expensive_operation(item)
        result.append(processed)
    return result
```

### Agent 分析流程

1. **代码分析**
   - 理解代码逻辑：遍历列表，对每个元素执行昂贵操作
   - 识别潜在问题：串行处理，没有优化

2. **代码搜索**
   - 搜索 `expensive_operation` 的实现
   - 查找相关的性能优化代码
   - 检查是否有类似的并行处理示例

3. **日志查询**
   - 查询 `process_data` 相关的性能日志
   - 检查执行时间

4. **综合分析**
   - 代码作用：处理数据列表，对每个元素执行昂贵操作
   - 性能问题：串行处理，没有利用并行处理能力
   - 建议：
     - 使用并行处理（如 `multiprocessing`, `concurrent.futures`）
     - 考虑批量处理
     - 添加缓存机制
     - 优化 `expensive_operation` 的实现

## 场景5：配置错误

### 问题描述

```
系统启动失败，错误信息：
ConfigurationError: Invalid database configuration: missing required field 'host'
```

### Agent 分析流程

1. **解析错误**
   - 提取关键词：`ConfigurationError`, `database configuration`, `missing host`

2. **代码搜索**
   - 搜索配置加载代码
   - 查找数据库配置相关的代码
   - 检查配置验证逻辑

3. **日志查询**
   - 查询配置加载相关的日志
   - 检查配置文件的路径和内容

4. **综合分析**
   - 根因：数据库配置缺少必需的 `host` 字段
   - 建议：
     - 检查配置文件（如 `application.yml`, `.env`）
     - 确保所有必需的配置字段都已设置
     - 验证配置格式是否正确
     - 检查环境变量是否正确加载

## 使用建议

1. **提供详细信息**: 尽量提供完整的错误信息、时间范围、相关操作等。

2. **使用上下文文件**: 如果问题涉及特定代码，提供相关代码片段可以提高分析准确性。

3. **分步分析**: 对于复杂问题，可以分步骤进行分析，先分析一个方面，再深入其他方面。

4. **结合日志**: 提供相关的日志内容可以帮助 Agent 更好地理解问题上下文。

5. **验证建议**: Agent 提供的建议需要结合实际环境进行验证和调整。

