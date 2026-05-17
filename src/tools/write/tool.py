from pathlib import Path
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "write",
    "description": "写入或覆盖文件内容（如文件已存在则覆盖）",
    "read_only": False,
    "concurrency_safe": False,
    "enabled": True,
    "permission": "ask",
    "params": [
        ParamSchema(name="file_path", description="文件路径（绝对或相对路径）", type="string", required=True, min_length=1),
        ParamSchema(name="content", description="要写入的内容", type="string", required=True),
    ],
}


def execute(file_path: str, content: str) -> str:
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入文件: {file_path}"
    except Exception as e:
        return f"错误: {str(e)}"