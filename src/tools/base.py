from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具基类，所有工具需要继承此类"""

    name: str = ""  # 工具名称
    description: str = ""  # 工具描述

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具逻辑，返回结果字符串"""
        pass

    def get_definition(self) -> dict[str, Any]:
        """返回工具的 OpenAI function calling 定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }