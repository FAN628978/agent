from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Skill:
    """技能实例"""
    name: str
    description: str   # 简短描述，用于列表展示
    content: str       # 完整 md 内容，加载到 prompt
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)