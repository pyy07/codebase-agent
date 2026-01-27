"""测试 AST 解析器配置模块"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from codebase_driven_agent.tools.ast_parser import get_ast_config, AST_AVAILABLE


def test_ast_parser():
    """测试 AST 解析器配置"""
    print("=" * 60)
    print("测试 AST 解析器配置模块")
    print("=" * 60)
    
    if not AST_AVAILABLE:
        print("❌ tree-sitter 未安装")
        print("请运行: pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript")
        return False
    
    print("✅ tree-sitter 已安装")
    
    # 获取配置实例
    config = get_ast_config()
    
    # 测试初始化
    print("\n测试初始化...")
    if config.initialize():
        print("✅ AST 解析器初始化成功")
        print(f"   支持的语言: {list(config.parsers.keys())}")
    else:
        print("❌ AST 解析器初始化失败")
        return False
    
    # 测试语言检测
    print("\n测试语言检测...")
    test_files = [
        "test.py",
        "test.js",
        "test.ts",
        "test.tsx",
        "test.java",
        "test.go",
        "unknown.txt"
    ]
    
    for file_path in test_files:
        lang = config.get_language_from_file(file_path)
        supported = config.is_language_supported(lang) if lang else False
        status = "✅" if supported else "⚠️"
        print(f"   {status} {file_path:15} -> {lang or '不支持'}")
    
    # 测试解析器获取
    print("\n测试解析器获取...")
    for lang in ['python', 'javascript', 'typescript']:
        parser = config.get_parser(lang)
        status = "✅" if parser else "❌"
        print(f"   {status} {lang:15} -> {'可用' if parser else '不可用'}")
    
    # 测试代码解析
    print("\n测试代码解析...")
    test_code_python = """
def hello_world():
    print("Hello, World!")
    return True
"""
    
    test_code_javascript = """
function helloWorld() {
    console.log("Hello, World!");
    return true;
}
"""
    
    test_cases = [
        ("test.py", test_code_python),
        ("test.js", test_code_javascript),
    ]
    
    for file_path, code in test_cases:
        tree = config.parse_file(file_path, code)
        status = "✅" if tree else "❌"
        print(f"   {status} {file_path:15} -> {'解析成功' if tree else '解析失败'}")
        if tree:
            print(f"      AST 根节点类型: {tree.root_node.type}")
            print(f"      子节点数量: {len(tree.root_node.children)}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_ast_parser()
    sys.exit(0 if success else 1)
