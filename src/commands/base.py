from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Command:
    """命令实例"""
    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    execute: Callable[..., str | None] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)