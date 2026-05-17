from enum import Enum
from typing import Any


class Permission(str, Enum):
    ALLOW = "allow"   # 直接执行
    ASK = "ask"       # 执行前需批准
    DENY = "deny"     # 禁止执行


def terminal_checker(tool_name: str, params: dict[str, Any]) -> bool:
    """终端交互式权限检查器，显示命令并等待用户批准"""
    import sys

    params_display = ", ".join(
        f"{k}={repr(v)[:50]}{'...' if len(repr(v)) > 50 else ''}"
        for k, v in params.items()
    )
    print(f"\n[批准?] 工具: {tool_name}", file=sys.stderr)
    print(f"         参数: {params_display}", file=sys.stderr)

    while True:
        print("> 批准 (y) / 拒绝 (n) / 全部批准 (a) / 全部拒绝 (d)? ", end="", file=sys.stderr)
        sys.stderr.flush()
        try:
            line = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("已拒绝（Ctrl+C）", file=sys.stderr)
            return False

        if line in ("y", "yes"):
            return True
        if line in ("n", "no"):
            return False
        if line == "a":
            return True
        if line == "d":
            return False
        print("  请输入 y / n / a / d", file=sys.stderr)


class ParamSchema:
    def __init__(
        self,
        name: str,
        description: str = "",
        type: str = "string",
        required: bool = True,
        default: Any = None,
        enum: list | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
    ):
        self.name = name
        self.description = description
        self.type = type
        self.required = required
        self.default = default
        self.enum = enum
        self.min_length = min_length
        self.max_length = max_length
        self.minimum = minimum
        self.maximum = maximum

    def to_openai_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        return schema


def validate(params: dict[str, Any], schema: list[ParamSchema]) -> tuple[bool, str | None]:
    for p in schema:
        value = params.get(p.name)
        if p.required and value is None:
            return False, f"缺少必需参数: {p.name}"
        if value is None:
            continue
        if p.enum and value not in p.enum:
            return False, f"参数 {p.name} 的值必须在 {p.enum} 中"
        if p.minimum is not None and isinstance(value, (int, float)) and value < p.minimum:
            return False, f"参数 {p.name} 不能小于 {p.minimum}"
        if p.maximum is not None and isinstance(value, (int, float)) and value > p.maximum:
            return False, f"参数 {p.name} 不能大于 {p.maximum}"
        if p.min_length is not None and isinstance(value, str) and len(value) < p.min_length:
            return False, f"参数 {p.name} 长度不能小于 {p.min_length}"
        if p.max_length is not None and isinstance(value, str) and len(value) > p.max_length:
            return False, f"参数 {p.name} 长度不能大于 {p.max_length}"
    return True, None