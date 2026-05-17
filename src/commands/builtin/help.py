from ..base import Command


def _build_help_text() -> str:
    from src.commands import get_command_loader

    loader = get_command_loader()
    lines = ["## 可用命令\n"]
    lines.append("| 命令   | 别名      | 说明          |")
    lines.append("|--------|-----------|--------------|")

    if loader:
        for cmd in loader.list_commands():
            alias_str = ", ".join(cmd["aliases"]) if cmd["aliases"] else "-"
            lines.append(f"| /{cmd['name']} | {alias_str} | {cmd['description']} |")
    else:
        lines.append("| (命令加载器未初始化) | - | - |")

    return "\n".join(lines)


command = Command(
    name="help",
    description="列出所有可用命令和工具",
    aliases=["h", "?"],
    execute=_build_help_text,
)