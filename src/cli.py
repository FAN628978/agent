import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent import Agent, AgentConfig
from src.tools.base import terminal_checker


async def main():
    config = AgentConfig(
        system_prompt_path=Path(__file__).parent / "SYSTEM_PROMPT.md",
        tools_enabled=True,
        skills_enabled=True,
    )
    agent = Agent(
        config,
        permission_checker=terminal_checker,
    )

    tool_names = [t["function"]["name"] for t in agent.available_tools]
    skill_names = [s["name"] for s in agent.available_skills]
    print(f"Agent 已启动，工具: {tool_names}")
    if skill_names:
        print(f"          技能: {skill_names}")
    print("输入 exit 退出\n")

    while True:
        user_input = input("> ")
        if user_input.lower() == "exit":
            break

        response = await agent.run_with_tools(user_input)
        # None 表示用户拒绝执行工具，回到输入循环
        if response is None:
            continue
        print(f"\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())