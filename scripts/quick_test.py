#!/usr/bin/env python3
"""快速测试脚本 - 验证服务是否正常工作"""
import sys
import os
import requests
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")


def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_health():
    """测试健康检查"""
    print_section("1. 健康检查")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ 健康检查通过: {response.json()}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 {BASE_URL}")
        print("   请确保服务已启动: uvicorn codebase_driven_agent.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_info():
    """测试服务信息"""
    print_section("2. 服务信息")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print(f"✅ 服务信息:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            return True
        else:
            print(f"❌ 获取服务信息失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_tools():
    """测试工具列表"""
    print_section("3. 工具列表")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/tools", timeout=5)
        if response.status_code == 200:
            tools = response.json()
            print(f"✅ 已注册 {len(tools)} 个工具:")
            for tool_name, tool_info in tools.items():
                status = "✅ 启用" if tool_info.get("enabled") else "❌ 禁用"
                print(f"   - {tool_name}: {status}")
            return True
        else:
            print(f"❌ 获取工具列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_analyze():
    """测试分析接口"""
    print_section("4. 分析接口测试")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    data = {
        "input": "这是一个测试请求，请简单回复确认收到。"
    }
    
    try:
        print(f"发送请求到: {BASE_URL}/api/v1/analyze")
        print(f"请求内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            json=data,
            headers=headers,
            timeout=60  # 分析可能需要较长时间
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 分析成功!")
            print(f"   状态: {result.get('status')}")
            if result.get('result'):
                result_data = result['result']
                print(f"   根因: {result_data.get('root_cause', 'N/A')[:100]}...")
                print(f"   置信度: {result_data.get('confidence', 0)}")
            if result.get('execution_time'):
                print(f"   执行时间: {result['execution_time']:.2f} 秒")
            return True
        elif response.status_code == 401:
            print(f"❌ 认证失败: 请检查 API_KEY 配置")
            return False
        else:
            print(f"❌ 分析失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（60秒）")
        print("   这可能是正常的，分析可能需要较长时间")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_cache():
    """测试缓存功能"""
    print_section("5. 缓存功能")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/cache/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            if stats.get("enabled"):
                print(f"✅ 缓存已启用:")
                print(f"   大小: {stats.get('size', 0)}/{stats.get('max_size', 0)}")
                print(f"   使用率: {stats.get('usage_percent', 0):.1f}%")
                print(f"   TTL: {stats.get('ttl', 0)} 秒")
            else:
                print(f"ℹ️  缓存未启用")
            return True
        else:
            print(f"ℹ️  缓存功能不可用")
            return True  # 不是错误
    except Exception as e:
        print(f"ℹ️  缓存功能不可用: {str(e)}")
        return True  # 不是错误


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Codebase Driven Agent - 快速测试")
    print("="*60)
    print(f"\n测试目标: {BASE_URL}")
    if API_KEY:
        print(f"API Key: {'*' * (len(API_KEY) - 4)}{API_KEY[-4:]}")
    else:
        print("API Key: 未设置（如果服务需要认证，请设置 API_KEY 环境变量）")
    
    results = []
    
    # 运行测试
    results.append(("健康检查", test_health()))
    
    if results[-1][1]:  # 如果健康检查通过，继续其他测试
        results.append(("服务信息", test_info()))
        results.append(("工具列表", test_tools()))
        results.append(("缓存功能", test_cache()))
        
        # 询问是否测试分析接口（可能需要较长时间）
        print("\n" + "-"*60)
        user_input = input("是否测试分析接口？（可能需要较长时间，需要 LLM API Key）[y/N]: ")
        if user_input.lower() in ['y', 'yes']:
            results.append(("分析接口", test_analyze()))
        else:
            print("跳过分析接口测试")
            results.append(("分析接口", None))
    
    # 汇总结果
    print_section("测试结果汇总")
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for name, result in results:
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⏭️  跳过"
        print(f"   {name}: {status}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed > 0:
        print("\n⚠️  部分测试失败，请检查:")
        print("   1. 服务是否正在运行")
        print("   2. 环境变量配置是否正确")
        print("   3. 查看服务日志了解详细错误")
        sys.exit(1)
    else:
        print("\n✅ 所有测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()

