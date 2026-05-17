import json
from typing import Callable

from openai import AsyncOpenAI
from .config import AgentConfig
from .types import Message


class OpenAIClient:
    def __init__(self, config: AgentConfig):
        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        self.config = config

    def _build_messages(self, messages: list[Message], system_prompt: str) -> list[dict]:
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for msg in messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    async def chat(self, messages: list[Message], system_prompt: str = "") -> str:
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=self._build_messages(messages, system_prompt),
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_with_tools(
        self,
        messages: list[Message],
        system_prompt: str = "",
        tools: list = None,
        tool_handler: Callable = None,
    ) -> str:
        tool_choice = "auto" if tools else None
        request_messages = self._build_messages(messages, system_prompt)

        while True:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=request_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                tools=tools,
                tool_choice=tool_choice,
            )

            choice = response.choices[0]
            message = choice.message

            if not message.tool_calls:
                return message.content or ""

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args_str = tool_call.function.arguments
                tc_id = tool_call.id or f"call_{id(tool_call)}"

                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                result = tool_handler(tool_call)

                request_messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tc_id,
                        "type": "function",
                        "function": {"name": name, "arguments": args_str},
                    }],
                })
                request_messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result,
                })