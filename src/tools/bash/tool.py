from src.tools.base import ParamSchema
from src.tools.bash.shell import execute as shell_execute


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
    return shell_execute(command, timeout)