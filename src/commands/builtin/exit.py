from ..base import Command


def do_exit() -> str | None:
    return "__EXIT__"


command = Command(
    name="exit",
    description="退出程序",
    aliases=["quit", "q"],
    execute=do_exit,
)