"""简单测试 AST 解析器（独立测试，不依赖项目其他模块）"""
import sys
from pathlib import Path

# 测试 tree-sitter 是否安装
print("=" * 60)
print("测试 tree-sitter 安装和基本功能")
print("=" * 60)

try:
    import tree_sitter
    print("✅ tree-sitter 核心库已安装")
except ImportError:
    print("❌ tree-sitter 核心库未安装")
    print("请运行: pip install tree-sitter")
    sys.exit(1)

# 测试语言解析器
languages_to_test = [
    ("tree_sitter_python", "python"),
    ("tree_sitter_javascript", "javascript"),
    ("tree_sitter_typescript", "typescript"),
    ("tree_sitter_cpp", "cpp"),
    ("tree_sitter_java", "java"),
]

available_languages = []

from tree_sitter import Language

for module_name, lang_name in languages_to_test:
    try:
        if module_name == "tree_sitter_typescript":
            import tree_sitter_typescript
            try:
                lang_obj = Language(tree_sitter_typescript.language_typescript())
            except AttributeError:
                lang_obj = Language(tree_sitter_typescript.language())
            available_languages.append((lang_name, lang_obj))
            print(f"✅ {lang_name} 语言解析器已安装")
        else:
            module = __import__(module_name)
            lang_func = getattr(module, "language")
            lang_obj = Language(lang_func())
            available_languages.append((lang_name, lang_obj))
            print(f"✅ {lang_name} 语言解析器已安装")
    except ImportError:
        print(f"❌ {lang_name} 语言解析器未安装")
        print(f"   请运行: pip install {module_name.replace('_', '-')}")
    except Exception as e:
        print(f"❌ {lang_name} 语言解析器加载失败: {e}")

if not available_languages:
    print("\n⚠️  没有可用的语言解析器")
    print("请至少安装一个语言解析器，例如:")
    print("  pip install tree-sitter-python")
    print("  pip install tree-sitter-javascript")
    print("  pip install tree-sitter-typescript")
    sys.exit(1)

# 测试基本解析功能
print("\n" + "=" * 60)
print("测试 AST 解析功能")
print("=" * 60)

from tree_sitter import Parser

for lang_name, lang_obj in available_languages:
    try:
        parser = Parser(lang_obj)
        
        # 测试代码
        if lang_name == "python":
            test_code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        elif lang_name in ["javascript", "typescript"]:
            test_code = """
function helloWorld() {
    console.log("Hello, World!");
    return true;
}
"""
        else:
            continue
        
        tree = parser.parse(bytes(test_code, 'utf8'))
        root_node = tree.root_node
        
        print(f"\n✅ {lang_name} 解析成功")
        print(f"   根节点类型: {root_node.type}")
        print(f"   子节点数量: {len(root_node.children)}")
        
        # 查找函数定义
        def find_functions(node):
            functions = []
            if node.type in ['function_definition', 'function_declaration', 'method_declaration', 'constructor_declaration']:
                functions.append(node)
            for child in node.children:
                functions.extend(find_functions(child))
            return functions
        
        functions = find_functions(root_node)
        if functions:
            print(f"   找到 {len(functions)} 个函数定义")
            for func in functions[:3]:  # 只显示前3个
                func_name = ""
                for child in func.children:
                    if child.type == 'identifier':
                        func_name = test_code[child.start_byte:child.end_byte]
                        break
                if func_name:
                    print(f"     - {func_name}")
        
    except Exception as e:
        print(f"❌ {lang_name} 解析失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print("\n依赖管理文件已更新:")
print("  - requirements.txt: 已添加 tree-sitter 相关依赖")
print("  - pyproject.toml: 已添加 tree-sitter 相关依赖")
print("\n在新环境中安装依赖:")
print("  pip install -r requirements.txt")
print("  或")
print("  pip install -e .")
