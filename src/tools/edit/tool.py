from pathlib import Path
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "edit",
    "description": "精确替换文件中的指定文本片段",
    "read_only": False,
    "concurrency_safe": False,
    "enabled": True,
    "permission": "ask",
    "params": [
        ParamSchema(name="file_path", description="文件路径", type="string", required=True, min_length=1),
        ParamSchema(name="old_string", description="待替换的原文本（必须精确匹配）", type="string", required=True, min_length=1),
        ParamSchema(name="new_string", description="替换后的新文本", type="string", required=True),
    ],
}


def execute(file_path: str, old_string: str, new_string: str) -> str:
    path = Path(file_path)
    if not path.exists():
        return f"错误: 文件不存在: {file_path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_string not in content:
            return f"错误: 未找到匹配内容: {old_string[:50]}..."
        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"已修改文件: {file_path}"
    except Exception as e:
        return f"错误: {str(e)}"