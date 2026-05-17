from pathlib import Path
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "glob",
    "description": "按 glob 模式查找文件路径",
    "read_only": True,
    "concurrency_safe": True,
    "enabled": True,
    "permission": "allow",
    "params": [
        ParamSchema(name="pattern", description="glob 模式，如 '**/*.py' 或 'src/**/*.ts'", type="string", required=True, min_length=1),
        ParamSchema(name="path", description="搜索根目录，省略则用当前目录", type="string", required=False),
    ],
}


def execute(pattern: str, path: str | None = None) -> str:
    root = Path(path) if path else Path.cwd()
    if not root.exists():
        return f"错误: 路径不存在: {path or '当前目录'}"
    try:
        matches = sorted(root.glob(pattern))
        if not matches:
            return "未找到匹配文件"
        lines = [str(m.relative_to(root)) if m.is_relative_to(root) else str(m) for m in matches]
        return f"共 {len(matches)} 个文件：\n" + "\n".join(lines)
    except Exception as e:
        return f"错误: {str(e)}"