import importlib.util
from pathlib import Path
from typing import Any

from src.tools.base import Permission, validate


class ToolLoader:
    def __init__(self, permission_checker: Any | None = None):
        self._metadata: dict[str, dict[str, Any]] = {}
        self._permission_checker = permission_checker  # (tool_name, params) -> bool | None

    def _load_tool_meta(self, tool_dir: Path) -> dict[str, Any] | None:
        tool_file = tool_dir / "tool.py"
        if not tool_file.exists():
            return None

        module_name = f"src.tools.{tool_dir.name}.tool"
        spec = importlib.util.spec_from_file_location(module_name, tool_file)
        if not (spec and spec.loader):
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        definition = getattr(module, "TOOL_DEFINITION", None)
        if not definition:
            return None

        return {
            "name": definition["name"],
            "description": definition["description"],
            "read_only": definition.get("read_only", False),
            "concurrency_safe": definition.get("concurrency_safe", False),
            "permission": definition.get("permission", Permission.ASK),
            "enabled": definition.get("enabled", False),
            "params": definition["params"],
            "_tool_dir": tool_dir,
            "_module_name": module_name,
        }

    def _build_definition(self, meta: dict[str, Any]) -> dict[str, Any]:
        properties = {}
        required = []
        for p in meta["params"]:
            properties[p.name] = p.to_openai_schema()
            if p.required:
                required.append(p.name)
        return {
            "type": "function",
            "function": {
                "name": meta["name"],
                "description": meta["description"],
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        }

    def load(self, tools_path: Path | None = None, enabled_only: bool = True) -> dict[str, dict[str, Any]]:
        self._metadata.clear()
        if tools_path is None:
            tools_path = Path(__file__).parent

        for item in tools_path.iterdir():
            if not item.is_dir() or not (item / "tool.py").exists():
                continue
            meta = self._load_tool_meta(item)
            if not meta:
                continue
            if enabled_only and not meta["enabled"]:
                continue
            self._metadata[meta["name"]] = meta

        return self._metadata

    def set_permission_checker(self, checker: Any) -> None:
        """设置权限检查器：(tool_name, params) -> bool | None"""
        self._permission_checker = checker

    def get_names(self) -> list[str]:
        return [name for name in self._metadata]

    def get_definitions(self) -> list[dict]:
        return [self._build_definition(m) for m in self._metadata.values()]

    def get_tool(self, name: str) -> dict[str, Any] | None:
        return self._metadata.get(name)

    def _check_permission(self, name: str, params: dict[str, Any]) -> tuple[bool, str | None]:
        """检查工具执行权限"""
        meta = self._metadata.get(name)
        if not meta:
            return False, f"工具 {name} 未加载"

        permission = Permission(meta.get("permission", Permission.ASK))

        if permission == Permission.DENY:
            return False, f"工具 {name} 被禁止执行"

        if permission == Permission.ALLOW:
            return True, None

        # ASK: 交给外部检查器
        if self._permission_checker:
            try:
                granted = self._permission_checker(name, params)
                if granted is True:
                    return True, None
                if granted is False:
                    return False, f"工具 {name} 执行被拒绝（需用户批准）"
                # None 表示未决定，继续提示
            except Exception as e:
                return False, f"权限检查出错: {e}"

        return False, f"工具 {name} 需要用户批准后方可执行"

    def execute(self, name: str, params: dict[str, Any]) -> str:
        """延迟加载并执行工具"""
        ok, reason = self._check_permission(name, params)
        if not ok:
            return reason or f"工具 {name} 执行被拒绝"

        ok, err = validate(params, self._metadata[name]["params"])
        if not ok:
            return f"输入错误: {err}"

        meta = self._metadata[name]
        spec = importlib.util.spec_from_file_location(meta["_module_name"], meta["_tool_dir"] / "tool.py")
        if not (spec and spec.loader):
            return f"错误: 无法加载工具 {name}"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        execute_fn = getattr(module, "execute", None)
        if not execute_fn:
            return f"错误: 工具 {name} 缺少 execute 函数"

        try:
            return execute_fn(**params)
        except Exception as e:
            return f"错误: {str(e)}"

    @property
    def tools(self) -> dict[str, dict[str, Any]]:
        return self._metadata