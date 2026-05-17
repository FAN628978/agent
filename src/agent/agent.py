import json
from pathlib import Path
from typing import Any

from .config import AgentConfig
from .types import Message
from src.tools import ToolLoader
from src.tools.base import ToolExecutionRefused


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        custom_tools_path: Path | None = None,
        tools_enabled: bool = True,
        skills_enabled: bool = True,
        custom_skills_path: Path | None = None,
        permission_checker: Any | None = None,
    ):
        self.config = config
        self.tools_enabled = tools_enabled
        self.skills_enabled = skills_enabled or getattr(config, "skills_enabled", True)
        self.messages: list[Message] = []
        self._active_skills: set[str] = set()

        if tools_enabled:
            self.tool_loader = ToolLoader(permission_checker=permission_checker)
            self.tool_loader.load(
                custom_tools_path if custom_tools_path is not None else config.custom_tools_path
            )
        else:
            self.tool_loader = None

        if self.skills_enabled:
            from src.skills import SkillLoader
            self.skill_loader = SkillLoader()
            self.skill_loader.load(
                custom_skills_path if custom_skills_path is not None else config.custom_skills_path
            )
        else:
            self.skill_loader = None

    def _build_system_prompt(self) -> str:
        parts = []
        if self.config.system_prompt:
            parts.append(self.config.system_prompt)

        if self.tool_loader:
            names = self.tool_loader.get_names()
            if names:
                parts.append(f"\n\n## 可用工具\n{', '.join(names)}")

        if self.skills_enabled and self.skill_loader:
            parts.append("\n\n## 可用技能")
            parts.append("需要使用某项技能时，明确告知用户。")
            parts.extend(self.skill_loader.get_prompt_parts())

        return "\n\n".join(parts) if parts else ""

    def _activate_skill(self, skill_name: str) -> None:
        if not self.skill_loader or skill_name in self._active_skills:
            return
        full_content = self.skill_loader.get_skill_prompt(skill_name)
        if full_content:
            self._active_skills.add(skill_name)
            self.messages.append(
                Message(role="system", content=f"[技能激活: {skill_name}]\n{full_content}")
            )

    def _check_skill_triggers(self, text: str) -> None:
        if not self.skill_loader or not text:
            return
        text_lower = text.lower()
        for skill in self.skill_loader.skills.values():
            if any(trigger in text_lower for trigger in skill.triggers):
                self._activate_skill(skill.name)
                continue
            name_parts = skill.name.replace("-", " ").split()
            if any(p in text_lower for p in name_parts):
                self._activate_skill(skill.name)

    async def run_with_tools(self, user_input: str) -> str | None:
        from .client import OpenAIClient

        self.messages.append(Message(role="user", content=user_input))
        self._check_skill_triggers(user_input)

        client = OpenAIClient(self.config)
        system_prompt = self._build_system_prompt()

        def handle_tool(tool_call) -> str:
            tool_name = tool_call.function.name
            args_str = tool_call.function.arguments
            if isinstance(args_str, str):
                args_str = args_str or "{}"
            try:
                tool_args = json.loads(args_str)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}
            try:
                result = self.tool_loader.execute(tool_name, tool_args)
            except ToolExecutionRefused:
                raise  # 向上传播，让 run_with_tools 捕获
            return result

        tools = self.tool_loader.get_definitions() if self.tools_enabled else None
        try:
            response = await client.chat_with_tools(
                messages=self.messages,
                system_prompt=system_prompt,
                tools=tools,
                tool_handler=handle_tool,
            )
        except ToolExecutionRefused:
            return None  # 用户拒绝执行，返回 None 表示需要重新输入

        self.messages.append(Message(role="assistant", content=response))
        self._check_skill_triggers(response)
        return response

    def reset(self):
        self.messages.clear()
        self._active_skills.clear()

    @property
    def available_tools(self) -> list[dict]:
        if self.tool_loader:
            return self.tool_loader.get_definitions()
        return []

    @property
    def available_skills(self) -> list[dict]:
        if self.skill_loader:
            return self.skill_loader.list_skills()
        return []