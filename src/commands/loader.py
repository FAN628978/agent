import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .base import Command

if TYPE_CHECKING:
    from src.agent.agent import Agent


class CommandLoader:
    """命令加载器，扫描 commands/builtin/ 目录加载命令"""

    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._agent: "Agent | None" = None

    def set_agent(self, agent: "Agent") -> None:
        """注入 agent 引用，供命令使用"""
        self._agent = agent

    def load(self) -> dict[str, Command]:
        """加载内置命令"""
        builtin_path = Path(__file__).parent / "builtin"
        self._commands.clear()

        if not builtin_path.exists():
            return self._commands

        for item in builtin_path.iterdir():
            if item.is_file() and item.suffix == ".py" and item.stem != "__init__":
                self._register_from_module(item.stem, item)

        return self._commands

    def _register_from_module(self, name: str, path: Path) -> None:
        """从 Python 模块加载命令注册"""
        import importlib.util
        module_name = f"src.commands.builtin.{name}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        cmd = getattr(module, "command", None)
        if isinstance(cmd, Command):
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd

    def match(self, text: str) -> tuple[Command, list[str]] | None:
        """匹配命令，返回 (command, args) 或 None"""
        t = text.strip()
        if not t.startswith("/"):
            return None

        parts = t[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        cmd = self._commands.get(cmd_name)
        if cmd:
            return cmd, args
        return None

    def list_commands(self) -> list[dict]:
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            result.append({"name": cmd.name, "description": cmd.description, "aliases": cmd.aliases})
        return result

    @property
    def commands(self) -> dict[str, Command]:
        return self._commands