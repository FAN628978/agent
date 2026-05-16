from pathlib import Path

from .types import Skill


class SkillLoader:
    """技能加载器，扫描目录加载 md 文件定义的技能"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def _load_skill_from_path(self, skill_dir: Path) -> Skill | None:
        """从技能目录加载 README.md"""
        readme = skill_dir / "README.md"
        if not readme.exists():
            return None

        content = readme.read_text(encoding="utf-8")
        return self._parse_skill(skill_dir.name, content)

    def _parse_skill(self, name: str, content: str) -> Skill:
        """解析 md 内容，提取描述和内容"""
        lines = content.strip().split("\n")
        description = ""
        for line in lines:
            if line.startswith("#"):
                description = line.lstrip("#").strip()
                break

        if not description and lines:
            description = lines[0].strip().lstrip("#").strip() or name

        return Skill(name=name, description=description, content=content)

    def _scan_directory(self, directory: Path) -> list[Skill]:
        """扫描目录下的所有技能"""
        skills = []
        if not directory.exists():
            return skills

        for item in directory.iterdir():
            if item.is_dir() and (item / "README.md").exists():
                skill = self._load_skill_from_path(item)
                if skill:
                    skills.append(skill)
        return skills

    def load_builtin(self) -> dict[str, Skill]:
        """加载内置技能"""
        builtin_path = Path(__file__).parent / "builtin"
        self._skills.clear()

        for skill in self._scan_directory(builtin_path):
            self._skills[skill.name] = skill

        return self._skills

    def load_custom(self, custom_path: Path | None = None) -> dict[str, Skill]:
        """加载用户自定义技能"""
        if custom_path is None:
            custom_path = Path(__file__).parent / "custom"

        for skill in self._scan_directory(custom_path):
            self._skills[skill.name] = skill

        return self._skills

    def load_all(self, custom_path: Path | None = None) -> dict[str, Skill]:
        """加载所有技能（内置 + 自定义）"""
        self.load_builtin()
        self.load_custom(custom_path)
        return self._skills

    def get_skill(self, name: str) -> Skill | None:
        """获取指定名称的技能"""
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """列出所有技能（名称 + 描述）"""
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]

    def get_prompt_parts(self) -> list[str]:
        """获取所有技能的 md 内容，用于注入 prompt"""
        parts = []
        for skill in self._skills.values():
            parts.append(f"\n## {skill.name}\n\n{skill.content}\n")
        return parts

    @property
    def skills(self) -> dict[str, Skill]:
        return self._skills