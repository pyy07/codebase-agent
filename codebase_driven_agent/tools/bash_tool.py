"""命令执行工具实现"""
import subprocess
import shlex
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.bash")

# 危险命令黑名单
DANGEROUS_COMMANDS = [
    'rm', 'del', 'delete', 'format', 'mkfs', 'dd',
    'shutdown', 'reboot', 'halt', 'poweroff',
    'sudo', 'su', 'chmod', 'chown',
    'wget', 'curl',  # 防止下载恶意文件
    'nc', 'netcat', 'telnet',  # 防止网络连接
    'python', 'python3', 'node', 'ruby',  # 防止执行任意代码
    'eval', 'exec', 'source', '.',  # Shell 内置危险命令
]

# 危险模式（正则表达式）
DANGEROUS_PATTERNS = [
    r'rm\s+-rf',  # rm -rf
    r'>\s+/dev/',  # 重定向到设备
    r'\|\s*sh\s*$',  # 管道到 shell
    r'\|\s*bash\s*$',  # 管道到 bash
    r'`.*`',  # 命令替换
    r'\$\(.*\)',  # 命令替换
]


class BashToolInput(BaseModel):
    """命令执行工具输入参数"""
    command: str = Field(..., description="要执行的 shell 命令")
    cwd: Optional[str] = Field(None, description="工作目录（相对于代码仓库根目录）。如果不指定，使用代码仓库根目录")


class BashTool(BaseCodebaseTool):
    """命令执行工具
    
    执行 shell 命令，支持安全限制。
    """
    
    name: str = "bash"
    description: str = (
        "执行 shell 命令。可以运行系统命令来获取信息、检查状态等。"
        "注意：出于安全考虑，某些危险命令（如 rm、sudo 等）被禁止执行。"
        "使用场景：检查文件系统、运行构建命令、查看系统信息等。"
        "参数：command（要执行的命令）、cwd（工作目录，可选）。"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "code_repo_path", settings.code_repo_path)
        object.__setattr__(self, "max_execution_time", 30)  # 最大执行时间（秒）
    
    def _is_dangerous_command(self, command: str):
        """检查命令是否危险"""
        # 检查命令黑名单
        parts = shlex.split(command)
        if parts:
            cmd_name = parts[0].lower()
            if cmd_name in DANGEROUS_COMMANDS:
                return True, f"命令 '{cmd_name}' 被禁止执行"
        
        # 检查危险模式
        import re
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return True, f"命令包含危险模式: {pattern}"
        
        return False, None
    
    def _execute(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
        
        Returns:
            ToolResult
        """
        try:
            # 安全检查
            is_dangerous, danger_reason = self._is_dangerous_command(command)
            if is_dangerous:
                return ToolResult(
                    success=False,
                    error=f"安全限制：{danger_reason}"
                )
            
            # 确定工作目录
            if cwd:
                if not self.code_repo_path:
                    return ToolResult(
                        success=False,
                        error="代码仓库路径未配置（CODE_REPO_PATH）。请先配置代码仓库路径。"
                    )
                
                repo_path = Path(self.code_repo_path)
                if not repo_path.exists():
                    return ToolResult(
                        success=False,
                        error=f"代码仓库路径不存在: {self.code_repo_path}"
                    )
                
                work_dir = repo_path / cwd
                if not work_dir.exists():
                    return ToolResult(
                        success=False,
                        error=f"工作目录不存在: {cwd}"
                    )
                if not work_dir.is_dir():
                    return ToolResult(
                        success=False,
                        error=f"工作目录不是目录: {cwd}"
                    )
            else:
                if self.code_repo_path:
                    work_dir = Path(self.code_repo_path)
                else:
                    work_dir = None
            
            # 执行命令
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(work_dir) if work_dir else None,
                    capture_output=True,
                    text=True,
                    timeout=self.max_execution_time,
                    encoding='utf-8',
                    errors='replace'
                )
            except subprocess.TimeoutExpired:
                return ToolResult(
                    success=False,
                    error=f"命令执行超时（超过 {self.max_execution_time} 秒）"
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"执行命令时发生错误: {str(e)}"
                )
            
            # 构建输出
            result_lines = []
            result_lines.append(f"命令: {command}")
            if cwd:
                result_lines.append(f"工作目录: {cwd}")
            result_lines.append(f"退出码: {result.returncode}")
            result_lines.append("")
            
            if result.stdout:
                result_lines.append("标准输出:")
                result_lines.append(result.stdout)
            
            if result.stderr:
                result_lines.append("")
                result_lines.append("标准错误:")
                result_lines.append(result.stderr)
            
            result_text = "\n".join(result_lines)
            
            # 检查是否需要截断
            truncated = False
            summary = None
            if len(result_text) > self.max_output_length:
                truncated_result, truncated = self._truncate_data(result_text, self.max_output_length)
                summary = f"命令执行完成，输出已截断"
                result_text = truncated_result
            
            # 如果退出码不为0，标记为失败
            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"命令执行失败（退出码: {result.returncode}）",
                    data=result_text,
                    truncated=truncated,
                    summary=summary
                )
            
            return ToolResult(
                success=True,
                data=result_text,
                truncated=truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"BashTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"执行命令时发生错误: {str(e)}"
            )
