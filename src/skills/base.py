from abc import ABC, abstractmethod
from typing import Any

from .types import SkillContext, SkillState, SkillStatus


class BaseSkill(ABC):
    """技能基类，所有技能需要继承此类"""

    name: str = ""
    description: str = ""
    skill_type: str = ""
    state: SkillState = SkillState.IDLE

    def start(self, task: str, **kwargs) -> SkillContext:
        """开始一次技能会话，返回初始上下文"""
        self.state = SkillState.RUNNING
        return self._build_context(task, **kwargs)

    @abstractmethod
    def step(self, context: SkillContext) -> tuple[SkillStatus, SkillContext]:
        """执行一步，返回 (状态, 更新后的上下文)"""
        pass

    def stop(self, context: SkillContext) -> SkillContext:
        """停止技能，清洗资源"""
        self.state = SkillState.IDLE
        return context

    def resume(self, context: SkillContext) -> tuple[SkillStatus, SkillContext]:
        """从 WAIT 状态恢复，继续执行"""
        self.state = SkillState.RUNNING
        return self.step(context)

    def get_definition(self) -> dict[str, Any]:
        """返回 OpenAI function calling 定义"""
        return {
            "type": "function",
            "function": {
                "name": f"skill_{self.name}",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "技能要完成的任务或目标"},
                    },
                    "required": ["task"],
                },
            },
        }

    def _build_context(self, task: str, **kwargs) -> SkillContext:
        import uuid
        from .types import SkillContext as SC
        return SC(
            skill_id=str(uuid.uuid4()),
            task=task,
            state=kwargs,
        )

    def _log_step(self, context: SkillContext, action: str, result: Any) -> None:
        """记录步骤到历史"""
        import datetime as dt
        context.steps.append({"action": action, "result": result})
        context.updated_at = dt.datetime.now()