from .base import Command
from .loader import CommandLoader

# 全局共享，在 cli.py 中初始化
_command_loader: CommandLoader | None = None


def set_command_loader(loader: CommandLoader) -> None:
    global _command_loader
    _command_loader = loader


def get_command_loader() -> CommandLoader | None:
    return _command_loader


__all__ = ["Command", "CommandLoader", "set_command_loader", "get_command_loader"]