import re
from pathlib import Path

from .types import Skill


class SkillLoader:
    """技能加载器，扫描 skills/ 目录加载 SKILL.md 定义的技能"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._dirs: dict[str, Path] = {}  # name -> skill dir path

    def _load_frontmatter(self, skill_dir: Path) -> dict | None:
        """只解析 frontmatter，不加载完整内容"""
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        text = skill_file.read_text(encoding="utf-8")

        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                fm_text = text[3:end].strip()
                return self._parse_frontmatter(fm_text)

        return None

    def _parse_frontmatter(self, fm_text: str) -> dict:
        meta = {}
        meta["name"] = self._fm_get(fm_text, "name")
        meta["description"] = self._fm_get(fm_text, "description")
        meta["version"] = self._fm_get(fm_text, "version", "1.0.0")
        meta["triggers"] = self._fm_get_list(fm_text, "triggers")
        meta["allowed_tools"] = self._fm_get_list(fm_text, "allowed-tools")
        return meta

    def _fm_get(self, text: str, key: str, default: str = "") -> str:
        m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.MULTILINE)
        return m.group(1).strip().strip('"').strip("'") if m else default

    def _fm_get_list(self, text: str, key: str) -> list[str]:
        m = re.search(rf"^{re.escape(key)}:\s*\n", text, re.MULTILINE)
        if not m:
            return []
        rest = text[m.end():]
        lines = rest.split("\n")
        result = []
        for line in lines:
            s = line.strip()
            if s.startswith("- "):
                result.append(s[2:])
            elif s and not s.startswith("-") and not s.startswith("#"):
                break
        return result

    def _scan_directory(self, directory: Path) -> list[Skill]:
        """扫描目录，只解析 frontmatter"""
        skills = []
        if not directory.exists():
            return skills

        for item in directory.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                meta = self._load_frontmatter(item)
                if meta and meta.get("name"):
                    skill = Skill(
                        name=meta["name"],
                        description=meta.get("description", ""),
                        version=meta.get("version", "1.0.0"),
                        allowed_tools=meta.get("allowed_tools", []),
                        triggers=meta.get("triggers", []),
                    )
                    self._dirs[skill.name] = item
                    skills.append(skill)
        return skills

    def load(self, extra_path: Path | None = None) -> dict[str, Skill]:
        """加载技能，扫描内置目录 + 可选自定义目录"""
        skills_path = Path(__file__).parent
        self._skills.clear()
        self._dirs.clear()

        for skill in self._scan_directory(skills_path):
            self._skills[skill.name] = skill

        if extra_path and extra_path.exists():
            for skill in self._scan_directory(extra_path):
                self._skills[skill.name] = skill

        return self._skills

    def load_all(self, custom_path: Path | None = None) -> dict[str, Skill]:
        return self.load(custom_path)

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description, "version": s.version}
            for s in self._skills.values()
        ]

    def get_prompt_parts(self) -> list[str]:
        parts = []
        for skill in self._skills.values():
            trigger_str = ", ".join(skill.triggers) if skill.triggers else skill.name
            parts.append(
                f"- **{skill.name}** ({skill.version}): {skill.description}\n"
                f"  触发: {trigger_str}"
            )
        return parts

    def get_skill_prompt(self, name: str) -> str | None:
        """按需加载：读取 SKILL.md + reference.md + examples.md"""
        skill = self._skills.get(name)
        if not skill:
            return None

        skill_dir = self._dirs.get(name)
        if not skill_dir:
            return None

        parts = []

        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            parts.append(skill_file.read_text(encoding="utf-8"))

        ref = skill_dir / "reference.md"
        if ref.exists():
            parts.append("\n\n## 参考资料\n\n" + ref.read_text(encoding="utf-8"))

        ex = skill_dir / "examples.md"
        if ex.exists():
            parts.append("\n\n## 示例\n\n" + ex.read_text(encoding="utf-8"))

        return "\n".join(parts)

    def get_skill_allowed_tools(self, name: str) -> list[str]:
        skill = self._skills.get(name)
        return skill.allowed_tools if skill else []

    @property
    def skills(self) -> dict[str, Skill]:
        return self._skills