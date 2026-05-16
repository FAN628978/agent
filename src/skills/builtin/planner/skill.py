import datetime

from src.skills.base import BaseSkill
from src.skills.types import SkillContext, SkillState, SkillStatus


class PlannerSkill(BaseSkill):
    """多步骤任务规划技能，将复杂目标分解为结构化步骤并写入计划文件"""

    name = "planner"
    description = "将复杂目标分解为结构化计划，支持迭代式完善。接收任务目标，逐步生成计划内容。"
    skill_type = "planner"
    PLAN_FILENAME = ".claude/plan.md"

    def start(self, task: str, **kwargs) -> SkillContext:
        ctx = super().start(task)
        ctx.state["phase"] = "analyzing"
        ctx.state["plan_lines"] = []
        return ctx

    def step(self, context: SkillContext) -> tuple[SkillStatus, SkillContext]:
        phase = context.state.get("phase", "analyzing")

        if phase == "analyzing":
            context.state["phase"] = "planning"
            context.state["plan_lines"].append(
                f"# Plan — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            context.state["plan_lines"].append(f"## Goal: {context.task}")
            context.state["plan_lines"].append("\n## Subtasks\n")
            self._log_step(context, "analyze", f"目标识别: {context.task}")
            return SkillStatus.CONTINUE, context

        if phase == "planning":
            if not context.state.get("subtasks_added"):
                context.state["plan_lines"].append("1. [ ] 理解需求")
                context.state["plan_lines"].append("2. [ ] 设计实现方案")
                context.state["plan_lines"].append("3. [ ] 编写代码")
                context.state["plan_lines"].append("4. [ ] 测试与验证")
                context.state["subtasks_added"] = True
                self._log_step(context, "add_subtasks", "添加4个子任务")
                return SkillStatus.WAIT, context

            plan_content = "\n".join(context.state["plan_lines"])
            context.state["phase"] = "done"
            context.state["plan_content"] = plan_content
            self._log_step(context, "finalize_plan", f"共 {len(context.state['plan_lines'])} 行")
            return SkillStatus.CONTINUE, context

        if phase == "done":
            self.state = SkillState.DONE
            return SkillStatus.DONE, context

        return SkillStatus.DONE, context


skill = PlannerSkill()