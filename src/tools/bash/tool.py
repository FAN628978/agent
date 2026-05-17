import subprocess
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "bash",
    "description": "在终端执行 shell 命令并返回标准输出",
    "read_only": False,
    "concurrency_safe": False,
    "enabled": True,
    "permission": "ask",
    "params": [
        ParamSchema(name="command", description="要执行的 shell 命令", type="string", required=True, min_length=1),
        ParamSchema(name="timeout", description="超时秒数", type="integer", required=False, default=30, minimum=1, maximum=300),
    ],
}


def execute(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout if result.stdout else result.stderr
        return output.strip() if output else "(空输出)"
    except subprocess.TimeoutExpired:
        return f"错误: 命令执行超时 ({timeout}s)"
    except Exception as e:
        return f"错误: {str(e)}"