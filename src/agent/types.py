from pydantic import BaseModel
from typing import Literal, Any


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ToolCall(BaseModel):
    id: str
    name: str
    input: dict[str, Any]


class ToolResult(BaseModel):
    tool_call_id: str
    output: str