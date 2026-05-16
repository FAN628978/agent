import importlib.util
from pathlib import Path

from .base import BaseSkill


class SkillLoader:
    """技能加载器，负责扫描和加载技能"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def _load_skill_from_path(self, skill_dir: Path) -> BaseSkill | None:
        """从技能目录加载技能"""
        skill_file = skill_dir / "skill.py"
        if not skill_file.exists():
            return None

        module_name = f"src.skills.{skill_dir.parent.name}.{skill_dir.name}.skill"
        spec = importlib.util.spec_from_file_location(module_name, skill_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "skill"):
                return module.skill
        return None

    def _scan_directory(self, directory: Path) -> list[BaseSkill]:
        """扫描目录下的所有技能"""
        skills = []
        if not directory.exists():
            return skills

        for item in directory.iterdir():
            if item.is_dir() and (item / "skill.py").exists():
                skill = self._load_skill_from_path(item)
                if skill:
                    skills.append(skill)
        return skills

    def load_builtin(self) -> dict[str, BaseSkill]:
        """加载内置技能"""
        builtin_path = Path(__file__).parent / "builtin"
        self._skills.clear()

        for skill in self._scan_directory(builtin_path):
            self._skills[skill.name] = skill

        return self._skills

    def load_custom(self, custom_path: Path | None = None) -> dict[str, BaseSkill]:
        """加载用户自定义技能"""
        if custom_path is None:
            custom_path = Path(__file__).parent / "custom"

        for skill in self._scan_directory(custom_path):
            self._skills[skill.name] = skill

        return self._skills

    def load_all(self, custom_path: Path | None = None) -> dict[str, BaseSkill]:
        """加载所有技能（内置 + 自定义）"""
        self.load_builtin()
        self.load_custom(custom_path)
        return self._skills

    def get_skill(self, name: str) -> BaseSkill | None:
        """获取指定名称的技能"""
        return self._skills.get(name)

    def get_definitions(self) -> list[dict]:
        """获取所有技能的 OpenAI 定义"""
        return [skill.get_definition() for skill in self._skills.values()]

    @property
    def skills(self) -> dict[str, BaseSkill]:
        return self._skills