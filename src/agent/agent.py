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
    ):
        self.config = config
        self.tools_enabled = tools_enabled
        self.messages: list[Message] = []

        if tools_enabled:
            self.tool_loader = ToolLoader()
            self.tool_loader.load_all(custom_tools_path)
        else:
            self.tool_loader = None

    def run(self, user_input: str) -> str:
        """运行对话（无工具版本）"""
        self.messages.append(Message(role="user", content=user_input))
        # TODO: 调用 LLM
        return "response"

    async def run_with_tools(self, user_input: str) -> str:
        """运行对话（带工具版本）"""
        from .client import OpenAIClient

        self.messages.append(Message(role="user", content=user_input))
        client = OpenAIClient(self.config)

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
            system_prompt=self.config.system_prompt,
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