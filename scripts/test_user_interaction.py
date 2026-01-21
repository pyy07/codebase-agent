"""用户交互功能测试脚本"""
import requests
import json
import time
import uuid
import sys

BASE_URL = "http://localhost:8000"

def test_user_interaction():
    """测试用户交互流程"""
    print("=" * 60)
    print("用户交互功能测试")
    print("=" * 60)
    
    # 1. 启动分析（使用模糊问题触发请求）
    print("\n1. 启动分析...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze/stream",
            json={
                "input": "我的代码出错了，帮我看看"  # 模糊问题，可能触发请求
            },
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        print(f"  状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ 请求失败: {response.text}")
            return False
        
    except requests.exceptions.ConnectionError:
        print("  ❌ 无法连接到服务器，请确保后端服务正在运行")
        print(f"  尝试连接: {BASE_URL}")
        return False
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        return False
    
    # 2. 监听 SSE 事件
    print("\n2. 监听 SSE 事件（最多等待30秒）...")
    request_id = None
    question = None
    context = None
    
    start_time = time.time()
    timeout = 30
    
    try:
        for line in response.iter_lines():
            if time.time() - start_time > timeout:
                print("  ⚠️  超时：未在30秒内收到 user_input_request 事件")
                break
                
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('event:'):
                    event_type = line_str.split(':', 1)[1].strip()
                    if event_type == 'user_input_request':
                        print(f"  ✅ 收到事件类型: {event_type}")
                elif line_str.startswith('data:'):
                    data_str = line_str.split(':', 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        if 'request_id' in data:
                            request_id = data['request_id']
                            question = data.get('question', '')
                            context = data.get('context', '')
                            print(f"  ✅ 收到用户输入请求:")
                            print(f"    Request ID: {request_id}")
                            print(f"    问题: {question}")
                            if context:
                                print(f"    上下文: {context}")
                            break
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"  ❌ 读取 SSE 流时出错: {e}")
        return False
    
    if not request_id:
        print("  ⚠️  未收到 user_input_request 事件")
        print("  提示: Agent 可能不需要用户输入")
        print("  建议: 使用更模糊的问题描述，或修改 prompt 强制触发请求")
        return False
    
    # 3. 提交用户回复
    print(f"\n3. 提交用户回复...")
    try:
        reply_response = requests.post(
            f"{BASE_URL}/api/v1/analyze/reply",
            json={
                "request_id": request_id,
                "reply": "错误信息是 FileNotFoundError: config.json not found"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"  状态码: {reply_response.status_code}")
        if reply_response.status_code == 200:
            result = reply_response.json()
            print(f"  响应: {result.get('message', 'N/A')}")
            print("  ✅ 用户回复提交成功")
            return True
        else:
            print(f"  ❌ 用户回复提交失败: {reply_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"  ❌ 提交回复时出错: {e}")
        return False

def main():
    """主函数"""
    print("\n开始测试用户交互功能...")
    print(f"后端地址: {BASE_URL}")
    print("\n提示: 如果测试失败，请确保：")
    print("  1. 后端服务正在运行 (python run_backend.py)")
    print("  2. Agent 配置正确（LLM API Key 等）")
    print("  3. 可能需要修改 prompt 来强制触发用户输入请求\n")
    
    success = test_user_interaction()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败或未完全验证")
        print("\n提示: 如果 Agent 没有请求用户输入，这是正常的")
        print("Agent 只在认为信息不足时才会请求用户输入")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
