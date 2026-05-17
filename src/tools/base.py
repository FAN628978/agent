from enum import Enum
from typing import Any


class ToolExecutionRefused(Exception):
    """工具执行被拒绝时抛出"""
    pass


class Permission(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


def terminal_checker(tool_name: str, params: dict, permission: str = "ask") -> bool:
    """根据权限决定是否需要用户批准"""
    import sys

    # 获取简要命令展示
    if tool_name == "bash" and "command" in params:
        cmd = params["command"]
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        cmd_display = f'{tool_name}("{cmd}")'
    elif tool_name == "read" and "file_path" in params:
        cmd_display = f'{tool_name}("{params["file_path"]}")'
    elif tool_name == "write" and "file_path" in params:
        cmd_display = f'{tool_name}("{params["file_path"]}")'
    elif tool_name == "edit" and "file_path" in params:
        cmd_display = f'{tool_name}("{params["file_path"]}")'
    elif tool_name == "glob" and "pattern" in params:
        cmd_display = f'{tool_name}("{params["pattern"]}")'
    elif tool_name == "grep" and "pattern" in params:
        cmd_display = f'{tool_name}("{params["pattern"]}")'
    else:
        first_val = next(iter(params.values()), "")
        if isinstance(first_val, str):
            val = first_val[:60] + "..." if len(first_val) > 60 else first_val
            cmd_display = f'{tool_name}("{val}")'
        else:
            cmd_display = tool_name

    # ALLOW: 直接显示并执行
    if permission == "allow":
        print(cmd_display, flush=True, file=sys.stderr)
        return True

    # DENY: 拒绝执行
    if permission == "deny":
        print(f"{cmd_display} - 禁止执行", flush=True, file=sys.stderr)
        return False

    # ASK: 显示交互式选择
    import os
    if os.name == "nt":
        import msvcrt

        selected = [0]
        last_sel = [-1]

        def draw():
            print(f"\r{cmd_display}", end="", flush=True, file=sys.stderr)
            if selected[0] == 0:
                print("  \033[92m[Yes]\033[0m  [No]  (↑↓ 切换, Enter 确认)", end="", flush=True, file=sys.stderr)
            else:
                print("  [Yes]  \033[91m[No]\033[0m  (↑↓ 切换, Enter 确认)", end="", flush=True, file=sys.stderr)

        draw()

        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b"\r" or ch == b"\n":
                    print(flush=True, file=sys.stderr)
                    return selected[0] == 0
                if ch in (b"\x00", b"\xe0"):
                    key = msvcrt.getch()
                    if key == b"H":
                        selected[0] = 0
                    elif key == b"P":
                        selected[0] = 1
                    if selected[0] != last_sel[0]:
                        last_sel[0] = selected[0]
                        draw()
                elif ch in (b"y", b"Y"):
                    print(flush=True, file=sys.stderr)
                    return True
                elif ch in (b"n", b"N"):
                    print(flush=True, file=sys.stderr)
                    return False
            else:
                import time
                time.sleep(0.05)

    else:
        import select
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            selected = [0]
            last_sel = [-1]

            def draw():
                print(f"\r{cmd_display}", end="", flush=True, file=sys.stderr)
                if selected[0] == 0:
                    print("  \033[92m[Yes]\033[0m  [No]  (↑↓ 切换, Enter 确认)", end="", flush=True, file=sys.stderr)
                else:
                    print("  [Yes]  \033[91m[No]\033[0m  (↑↓ 切换, Enter 确认)", end="", flush=True, file=sys.stderr)

            draw()

            while True:
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready:
                    ch = sys.stdin.read(1)
                    if ch in ("\n", ""):
                        print(flush=True, file=sys.stderr)
                        return selected[0] == 0
                    elif ch == "\x1b":
                        nxt = sys.stdin.read(2)
                        if nxt == "[A":
                            selected[0] = 0
                        elif nxt == "[B":
                            selected[0] = 1
                        if selected[0] != last_sel[0]:
                            last_sel[0] = selected[0]
                            draw()
                    elif ch in ("y", "Y"):
                        print(flush=True, file=sys.stderr)
                        return True
                    elif ch in ("n", "N"):
                        print(flush=True, file=sys.stderr)
                        return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


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