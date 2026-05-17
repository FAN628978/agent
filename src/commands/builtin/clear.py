from ..base import Command


def do_clear() -> str:
    from src.commands import get_command_loader

    loader = get_command_loader()
    if loader and loader._agent:
        loader._agent.reset()
    return "对话历史已清空"


command = Command(
    name="clear",
    description="清空对话历史",
    aliases=["clr"],
    execute=do_clear,
)