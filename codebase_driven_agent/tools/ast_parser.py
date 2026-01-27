"""AST 解析器配置模块"""
import os
from pathlib import Path
from typing import Optional, Dict
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.ast_parser")

# AST 支持检查
try:
    import tree_sitter
    from tree_sitter import Language, Parser
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False
    logger.debug("tree-sitter not available, AST features will be disabled")
    Language = None
    Parser = None


class ASTParserConfig:
    """AST 解析器配置类"""
    
    # 支持的语言映射
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
    }
    
    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化 AST 解析器
        
        Returns:
            bool: 是否成功初始化
        """
        if not AST_AVAILABLE:
            logger.warning("tree-sitter not available, cannot initialize AST parser")
            return False
        
        if self._initialized:
            return True
        
        try:
            # 尝试加载 Python 语言解析器
            try:
                import tree_sitter_python
                python_lang = Language(tree_sitter_python.language())
                self.languages['python'] = python_lang
                logger.info("Loaded tree-sitter Python language parser")
            except ImportError:
                logger.warning("tree-sitter-python not installed, Python AST parsing will be disabled")
            except Exception as e:
                logger.warning(f"Failed to load Python language parser: {e}")
            
            # 尝试加载 JavaScript 语言解析器
            try:
                import tree_sitter_javascript
                javascript_lang = Language(tree_sitter_javascript.language())
                self.languages['javascript'] = javascript_lang
                logger.info("Loaded tree-sitter JavaScript language parser")
            except ImportError:
                logger.warning("tree-sitter-javascript not installed, JavaScript AST parsing will be disabled")
            except Exception as e:
                logger.warning(f"Failed to load JavaScript language parser: {e}")
            
            # 尝试加载 TypeScript 语言解析器
            try:
                import tree_sitter_typescript
                # tree-sitter-typescript 可能使用不同的 API
                try:
                    # 尝试使用 language_typescript() 函数
                    typescript_lang = Language(tree_sitter_typescript.language_typescript())
                except AttributeError:
                    # 如果不存在，尝试直接使用 language 属性
                    typescript_lang = Language(tree_sitter_typescript.language())
                self.languages['typescript'] = typescript_lang
                logger.info("Loaded tree-sitter TypeScript language parser")
            except ImportError:
                logger.warning("tree-sitter-typescript not installed, TypeScript AST parsing will be disabled")
            except Exception as e:
                logger.warning(f"Failed to load TypeScript language parser: {e}")
            
            # 尝试加载 C++ 语言解析器
            try:
                import tree_sitter_cpp
                cpp_lang = Language(tree_sitter_cpp.language())
                self.languages['cpp'] = cpp_lang
                logger.info("Loaded tree-sitter C++ language parser")
            except ImportError:
                logger.warning("tree-sitter-cpp not installed, C++ AST parsing will be disabled")
            except Exception as e:
                logger.warning(f"Failed to load C++ language parser: {e}")
            
            # 尝试加载 Java 语言解析器
            try:
                import tree_sitter_java
                java_lang = Language(tree_sitter_java.language())
                self.languages['java'] = java_lang
                logger.info("Loaded tree-sitter Java language parser")
            except ImportError:
                logger.warning("tree-sitter-java not installed, Java AST parsing will be disabled")
            except Exception as e:
                logger.warning(f"Failed to load Java language parser: {e}")
            
            # 为每种语言创建解析器
            for lang_name, lang_obj in self.languages.items():
                parser = Parser(lang_obj)
                self.parsers[lang_name] = parser
                logger.debug(f"Created parser for {lang_name}")
            
            self._initialized = True
            logger.info(f"AST parser initialized with {len(self.parsers)} language(s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AST parser: {e}", exc_info=True)
            return False
    
    def get_language_from_file(self, file_path: str) -> Optional[str]:
        """根据文件路径推断语言类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 语言名称，如果无法识别则返回 None
        """
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_MAP.get(ext)
    
    def get_parser(self, language: str) -> Optional[Parser]:
        """获取指定语言的解析器
        
        Args:
            language: 语言名称（python, javascript, typescript 等）
            
        Returns:
            Optional[Parser]: 解析器实例，如果语言不支持则返回 None
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        return self.parsers.get(language)
    
    def is_language_supported(self, language: str) -> bool:
        """检查语言是否支持 AST 解析
        
        Args:
            language: 语言名称
            
        Returns:
            bool: 是否支持
        """
        if not self._initialized:
            self.initialize()
        
        return language in self.parsers
    
    def parse_file(self, file_path: str, source_code: str) -> Optional[tree_sitter.Tree]:
        """解析代码文件为 AST
        
        Args:
            file_path: 文件路径（用于推断语言）
            source_code: 源代码内容
            
        Returns:
            Optional[tree_sitter.Tree]: AST 树，如果解析失败则返回 None
        """
        if not AST_AVAILABLE:
            return None
        
        language = self.get_language_from_file(file_path)
        if not language:
            logger.debug(f"Language not supported for file: {file_path}")
            return None
        
        parser = self.get_parser(language)
        if not parser:
            logger.debug(f"Parser not available for language: {language}")
            return None
        
        try:
            tree = parser.parse(bytes(source_code, 'utf8'))
            return tree
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}", exc_info=True)
            return None


# 全局 AST 解析器配置实例
_ast_config: Optional[ASTParserConfig] = None


def get_ast_config() -> ASTParserConfig:
    """获取全局 AST 解析器配置实例
    
    Returns:
        ASTParserConfig: AST 解析器配置实例
    """
    global _ast_config
    if _ast_config is None:
        _ast_config = ASTParserConfig()
        _ast_config.initialize()
    return _ast_config
