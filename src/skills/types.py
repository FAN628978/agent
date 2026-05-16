from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Skill:
    """技能实例"""
    name: str
    description: str
    version: str = "1.0.0"
    allowed_tools: list[str] = field(default_factory=list)
    content: str = ""          # 完整 md 内容，按需加载
    triggers: list[str] = field(default_factory=list)  # 触发词列表
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)