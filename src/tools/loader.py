import importlib.util
from pathlib import Path

from .base import BaseTool


class ToolLoader:
    """工具加载器，负责扫描和加载工具"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def _load_tool_from_path(self, tool_dir: Path) -> BaseTool | None:
        """从工具目录加载工具"""
        tool_file = tool_dir / "tool.py"
        if not tool_file.exists():
            return None

        module_name = f"src.tools.{tool_dir.parent.name}.{tool_dir.name}.tool"
        spec = importlib.util.spec_from_file_location(module_name, tool_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "tool"):
                return module.tool
        return None

    def _scan_directory(self, directory: Path) -> list[BaseTool]:
        """扫描目录下的所有工具"""
        tools = []
        if not directory.exists():
            return tools

        for item in directory.iterdir():
            if item.is_dir() and (item / "tool.py").exists():
                tool = self._load_tool_from_path(item)
                if tool:
                    tools.append(tool)
        return tools

    def load_builtin(self) -> dict[str, BaseTool]:
        """加载内置工具"""
        builtin_path = Path(__file__).parent / "builtin"
        self._tools.clear()

        for tool in self._scan_directory(builtin_path):
            self._tools[tool.name] = tool

        return self._tools

    def load_custom(self, custom_path: Path | None = None) -> dict[str, BaseTool]:
        """加载用户自定义工具"""
        if custom_path is None:
            custom_path = Path(__file__).parent / "custom"

        for tool in self._scan_directory(custom_path):
            self._tools[tool.name] = tool

        return self._tools

    def load_all(self, custom_path: Path | None = None) -> dict[str, BaseTool]:
        """加载所有工具（内置 + 自定义）"""
        self.load_builtin()
        self.load_custom(custom_path)
        return self._tools

    def get_tool(self, name: str) -> BaseTool | None:
        """获取指定名称的工具"""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict]:
        """获取所有工具的 OpenAI 定义"""
        return [tool.get_definition() for tool in self._tools.values()]

    @property
    def tools(self) -> dict[str, BaseTool]:
        return self._tools