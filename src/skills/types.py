from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SkillState(Enum):
    """技能生命周期状态"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"


class SkillStatus(Enum):
    """step() 的返回值，决定 agent 下一轮行为"""
    CONTINUE = "continue"  # 继续调用 step
    DONE = "done"          # 技能执行完成
    WAIT = "wait"          # 暂停，等待 LLM 或用户补充信息后 resume
    ERROR = "error"        # 不可恢复错误


@dataclass
class SkillContext:
    """每次 step 之间传递的上下文，承载 skill 的状态"""
    skill_id: str
    task: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)