import json
from pathlib import Path

from .config import AgentConfig
from .types import Message
from src.tools import ToolLoader


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        custom_tools_path: Path | None = None,
        tools_enabled: bool = True,
        skills_enabled: bool = True,
        custom_skills_path: Path | None = None,
    ):
        self.config = config
        self.tools_enabled = tools_enabled
        self.skills_enabled = skills_enabled
        self.messages: list[Message] = []

        if tools_enabled:
            self.tool_loader = ToolLoader()
            self.tool_loader.load_all(
                custom_tools_path if custom_tools_path is not None else config.custom_tools_path
            )
        else:
            self.tool_loader = None

        if skills_enabled:
            from src.skills import SkillLoader
            self.skill_loader = SkillLoader()
            self.skill_loader.load_all(
                custom_skills_path if custom_skills_path is not None else config.custom_skills_path
            )
        else:
            self.skill_loader = None

    def _build_system_prompt(self) -> str:
        """构建完整的 system prompt，包含技能 md 内容"""
        parts = []
        if self.config.system_prompt:
            parts.append(self.config.system_prompt)

        if self.skills_enabled and self.skill_loader:
            parts.append("\n\n## 技能 (Skills)")
            parts.extend(self.skill_loader.get_prompt_parts())

        return "\n\n".join(parts) if parts else ""

    async def run_with_tools(self, user_input: str) -> str:
        """运行对话（带工具和技能）"""
        from .client import OpenAIClient

        self.messages.append(Message(role="user", content=user_input))
        client = OpenAIClient(self.config)
        system_prompt = self._build_system_prompt()

        def handle_tool(tool_call) -> str:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
            tool = self.tool_loader.get_tool(tool_name)
            if tool:
                return tool.execute(**tool_args)
            return f"错误: 找不到工具 {tool_name}"

        tools = self.tool_loader.get_definitions() if self.tools_enabled else None
        response = await client.chat_with_tools(
            messages=self.messages,
            system_prompt=system_prompt,
            tools=tools,
            tool_handler=handle_tool,
        )

        self.messages.append(Message(role="assistant", content=response))
        return response

    def reset(self):
        self.messages.clear()

    @property
    def available_tools(self) -> list[dict]:
        """获取可用工具列表"""
        if self.tool_loader:
            return self.tool_loader.get_definitions()
        return []

    @property
    def available_skills(self) -> list[dict]:
        """获取可用技能列表"""
        if self.skill_loader:
            return self.skill_loader.list_skills()
        return []