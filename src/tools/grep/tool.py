import re
from pathlib import Path
from typing import Any

from src.tools.base import ParamSchema


TOOL_DEFINITION = {
    "name": "grep",
    "description": "在文件或目录下搜索匹配指定模式的文本行",
    "read_only": True,
    "concurrency_safe": True,
    "enabled": True,
    "permission": "allow",
    "params": [
        ParamSchema(name="pattern", description="搜索正则表达式", type="string", required=True, min_length=1),
        ParamSchema(name="path", description="搜索目录或文件路径", type="string", required=True, min_length=1),
        ParamSchema(name="glob", description="文件过滤 glob 模式，如 '*.py'，省略则搜索所有文件", type="string", required=False),
        ParamSchema(name="max_results", description="最大返回行数", type="integer", required=False, default=50, minimum=1, maximum=500),
    ],
}


def execute(pattern: str, path: str, glob: str | None = None, max_results: int = 50) -> str:
    target = Path(path)
    if not target.exists():
        return f"错误: 路径不存在: {path}"
    matches = []
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"错误: 无效正则: {e}"
    try:
        for f in target.rglob(glob or "*"):
            if not f.is_file() or f.suffix in (".pyc", ".pyo"):
                continue
            try:
                with open(f, encoding="utf-8", errors="ignore") as fp:
                    for lineno, line in enumerate(fp, 1):
                        if regex.search(line):
                            matches.append(f"{f}:{lineno}:{line.rstrip()}")
                            if len(matches) >= max_results:
                                break
            except Exception:
                continue
            if len(matches) >= max_results:
                break
        if not matches:
            return "未找到匹配"
        if len(matches) == max_results:
            return "达到结果上限（仅显示前 50 条）：\n" + "\n".join(matches)
        return "\n".join(matches)
    except Exception as e:
        return f"错误: {str(e)}"