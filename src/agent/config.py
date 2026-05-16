import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class AgentConfig(BaseModel):
    model: str = os.getenv("OPENAI_MODEL", "MiniMax-M2.5")
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    custom_tools_path: Path | None = None
    tools_enabled: bool = True
    skills_enabled: bool = True
    custom_skills_path: Path | None = None

    def model_post_init(self, _) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")

        if self.base_url is None:
            self.base_url = os.getenv("OPENAI_BASE_URL")