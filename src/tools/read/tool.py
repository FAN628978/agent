import re
from pathlib import Path
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "read",
    "description": "读取文件内容，支持指定行范围",
    "read_only": True,
    "concurrency_safe": True,
    "enabled": True,
    "permission": "allow",
    "params": [
        ParamSchema(name="file_path", description="文件路径（绝对或相对路径）", type="string", required=True, min_length=1),
        ParamSchema(name="offset", description="起始行号（1-based），省略则从头读", type="integer", required=False, default=1, minimum=1),
        ParamSchema(name="limit", description="最多读取行数，省略则读到末尾", type="integer", required=False, default=0, minimum=0),
    ],
}


def execute(file_path: str, offset: int = 1, limit: int = 0) -> str:
    path = Path(file_path)
    if not path.exists():
        return f"错误: 文件不存在: {file_path}"
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        start = max(0, offset - 1)
        end = len(lines) if limit <= 0 else min(start + limit, len(lines))
        return "".join(f"{i+1}\t{line}" for i, line in enumerate(lines[start:end], start=start + 1))
    except Exception as e:
        return f"错误: {str(e)}"