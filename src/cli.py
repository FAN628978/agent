import sys
from pathlib import Path
import platform

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent import Agent, AgentConfig


def _get_input(prompt_text: str) -> str:
    """跨平台输入：Linux 用 prompt_toolkit，Windows/macOS 用标准 input"""
    if platform.system() == "Linux":
        from prompt_toolkit import PromptSession
        session = PromptSession(prompt_text, erase_when_done=True)
        return session.prompt()
    else:
        return input(prompt_text)


async def main():
    config = AgentConfig(
        system_prompt="你是一个有帮助的 AI 助手，可以调用工具来完成任务。",
        tools_enabled=True,
        skills_enabled=True,
    )
    agent = Agent(config)

    tool_names = [t['function']['name'] for t in agent.available_tools]
    skill_names = [s['name'] for s in agent.available_skills]
    print(f"Agent 已启动，工具: {tool_names}")
    if skill_names:
        print(f"          技能: {skill_names}")
    print("输入 exit 退出\n")

    while True:
        try:
            user_input = _get_input("> ")
        except (KeyboardInterrupt, EOFError):
            print()
            continue

        if user_input.lower() == "exit":
            break

        response = await agent.run_with_tools(user_input)
        print(f"\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())