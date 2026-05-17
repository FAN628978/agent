import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent import Agent, AgentConfig
from src.tools.base import terminal_checker
from agent.client import enable_logging
from src.commands import CommandLoader, set_command_loader


async def main():
    enable_logging()
    config = AgentConfig(
        system_prompt_path=Path(__file__).parent / "SYSTEM_PROMPT.md",
        tools_enabled=True,
        skills_enabled=True,
    )
    agent = Agent(
        config,
        permission_checker=terminal_checker,
    )

    cmd_loader = CommandLoader()
    cmd_loader.set_agent(agent)
    cmd_loader.load()
    set_command_loader(cmd_loader)

    tool_names = [t["function"]["name"] for t in agent.available_tools]
    skill_names = [s["name"] for s in agent.available_skills]
    print(f"Agent 已启动，工具: {tool_names}")
    if skill_names:
        print(f"          技能: {skill_names}")
    print("输入 exit 退出\n")

    while True:
        user_input = input("> ")
        if not user_input.strip():
            continue

        # 兼容无前缀的 exit
        if user_input.lower() == "exit":
            break

        matched = cmd_loader.match(user_input)
        if matched:
            cmd, args = matched
            result = cmd.execute(*args)
            if result and result != "__EXIT__":
                print(result)
            if result == "__EXIT__" or cmd.name == "exit":
                break
            continue

        response = await agent.run_with_tools(user_input)
        if response is None:
            continue
        print(f"\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())