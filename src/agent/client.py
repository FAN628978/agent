import asyncio
import json
import socket
from urllib.parse import urlparse
from typing import Callable

from openai import AsyncOpenAI
from .config import AgentConfig
from .types import Message

# LLM 调用日志钩子
from src.hooks.logging import LLMLogger

_logger: LLMLogger | None = None


def enable_logging(log_path=None) -> None:
    """启用 LLM 调用日志，默认写入项目根目录"""
    global _logger
    if log_path is None:
        from pathlib import Path
        log_path = Path(__file__).parent.parent.parent / "llm_calls.txt"
    _logger = LLMLogger(log_path=log_path)


class OpenAIClient:
    def __init__(self, config: AgentConfig):
        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        self.config = config

    def _parse_url(self, url: str) -> tuple[str, int]:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return host, port

    def _ping_port(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (TimeoutError, OSError):
            return False

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
            call_id = _logger.log_request(request_messages, self.config.model, tools) if _logger else 0

            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=request_messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    tools=tools,
                    tool_choice=tool_choice,
                )
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            except Exception as e:
                if _logger:
                    _logger.log_response(call_id, None, None, error=str(e))
                # 本地大模型未响应，ping 端口检测，每 3s 一次，共 30s
                print(f"API 连接失败，{self.config.base_url}，正在等待服务就绪...", flush=True)
                host, port = self._parse_url(self.config.base_url)
                connected = False
                for attempt in range(1, 11):  # 10 次 x 3s = 30s
                    await asyncio.sleep(3)
                    if self._ping_port(host, port):
                        print(f"服务已就绪 (尝试 {attempt}/10)，正在请求...", flush=True)
                        try:
                            response = await self.client.chat.completions.create(
                                model=self.config.model,
                                messages=request_messages,
                                max_tokens=self.config.max_tokens,
                                temperature=self.config.temperature,
                                tools=tools,
                                tool_choice=tool_choice,
                            )
                            usage = {
                                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                                "total_tokens": response.usage.total_tokens if response.usage else 0,
                            }
                            connected = True
                            break
                        except Exception:
                            print(f"  服务端口已通但请求仍失败，继续等待...", flush=True)
                    else:
                        print(f"  等待中 {attempt}/10 ...", flush=True)
                if not connected:
                    print("API超时，请确认本地模型服务是否启动", flush=True)
                    if _logger:
                        _logger.flush()
                    return None

            choice = response.choices[0]
            message = choice.message

            if _logger:
                tc_list = []
                for tc in (message.tool_calls or []):
                    fname = tc.function.name
                    fargs = tc.function.arguments
                    if isinstance(fargs, str):
                        try: fargs = json.loads(fargs)
                        except: pass
                    tc_list.append({"name": fname, "arguments": fargs})
                _logger.log_response(call_id, message.content, tc_list, usage=usage)

            if not message.tool_calls:
                if _logger:
                    _logger.flush()
                return message.content or ""

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args_str = tool_call.function.arguments
                tc_id = tool_call.id or f"call_{id(tool_call)}"

                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                result = tool_handler(tool_call)
                if _logger:
                    _logger.log_tool_result(call_id, name, result)

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

            # 处理完所有工具调用后，继续发回 LLM 获取下一轮响应
            continue