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

    def run(self, user_input: str) -> str:
        """运行对话（无工具版本）"""
        self.messages.append(Message(role="user", content=user_input))
        # TODO: 调用 LLM
        return "response"

    async def run_with_tools(self, user_input: str) -> str:
        """运行对话（带工具和技能版本）"""
        from .client import OpenAIClient

        self.messages.append(Message(role="user", content=user_input))
        client = OpenAIClient(self.config)

        def handle_tool(tool_call) -> str:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
            if tool_name.startswith("skill_"):
                return self._handle_skill(tool_name, **tool_args)
            tool = self.tool_loader.get_tool(tool_name)
            if tool:
                return tool.execute(**tool_args)
            return f"错误: 找不到工具 {tool_name}"

        tools = []
        if self.tools_enabled:
            tools.extend(self.tool_loader.get_definitions())
        if self.skills_enabled:
            tools.extend(self.skill_loader.get_definitions())
        tools = tools if tools else None

        response = await client.chat_with_tools(
            messages=self.messages,
            system_prompt=self.config.system_prompt,
            tools=tools,
            tool_handler=handle_tool,
        )

        self.messages.append(Message(role="assistant", content=response))
        return response

    def _handle_skill(self, skill_name: str, **kwargs) -> str:
        """执行技能，循环 step 直到完成或等待"""
        skill = self.skill_loader.get_skill(skill_name.removeprefix("skill_"))
        if not skill:
            return f"错误: 找不到技能 {skill_name}"

        task = kwargs.get("task", "")
        context = skill.start(task)
        MAX_STEPS = 50
        steps = 0

        while steps < MAX_STEPS:
            status, context = skill.step(context)
            steps += 1

            if status.value == "done":
                return self._format_skill_result(context)
            if status.value == "error":
                return f"技能执行错误: {context.state.get('error', 'unknown')}"
            if status.value == "wait":
                # WAIT 状态暂停，等 LLM 下一轮补充后 resume
                return self._format_skill_result(context, waiting=True)

        return f"技能执行超过最大步数限制 ({MAX_STEPS} 步)"

    def _format_skill_result(self, context, waiting: bool = False) -> str:
        """格式化技能结果返回给 LLM"""
        parts = [f"[Skill '{context.skill_id}' {'等待补充' if waiting else '完成'}]"]
        parts.append(f"Task: {context.task}")
        if context.state.get("plan_content"):
            parts.append(f"\nPlan:\n{context.state['plan_content']}")
        if context.state.get("llm_input"):
            parts.append(f"\n补充输入: {context.state['llm_input']}")
        parts.append(f"Steps: {len(context.steps)}")
        return "\n".join(parts)

    def reset(self):
        self.messages.clear()

    @property
    def available_tools(self) -> list[dict]:
        """获取可用工具列表（含内置工具和技能）"""
        result = []
        if self.tool_loader:
            result.extend(self.tool_loader.get_definitions())
        if self.skill_loader:
            result.extend(self.skill_loader.get_definitions())
        return result