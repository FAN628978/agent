import re
from pathlib import Path

from .types import Skill


class SkillLoader:
    """技能加载器，支持按需加载"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._dirs: dict[str, Path] = {}  # name -> skill dir path

    def _load_frontmatter(self, skill_dir: Path) -> dict | None:
        """只解析 frontmatter，不加载完整内容"""
        readme = skill_dir / "README.md"
        if not readme.exists():
            return None

        text = readme.read_text(encoding="utf-8")

        # 解析 frontmatter --- ... ---
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                fm_text = text[3:end].strip()
                return self._parse_frontmatter(fm_text)

        return None

    def _parse_frontmatter(self, fm_text: str) -> dict:
        """解析 YAML-like frontmatter"""
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
                # 遇到非列表行（空行或其他 key），停止
                if not result and s.startswith(key):
                    continue
                break
        return result

    def _scan_directory(self, directory: Path) -> list[Skill]:
        """扫描目录，只解析 frontmatter"""
        skills = []
        if not directory.exists():
            return skills

        for item in directory.iterdir():
            if item.is_dir() and (item / "README.md").exists():
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

    def load_builtin(self) -> dict[str, Skill]:
        """加载内置技能（只解析 frontmatter）"""
        builtin_path = Path(__file__).parent / "builtin"
        self._skills.clear()
        self._dirs.clear()

        for skill in self._scan_directory(builtin_path):
            self._skills[skill.name] = skill

        return self._skills

    def load_custom(self, custom_path: Path | None = None) -> dict[str, Skill]:
        """加载自定义技能（只解析 frontmatter）"""
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
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """列出所有技能（名称 + 描述）"""
        return [
            {"name": s.name, "description": s.description, "version": s.version}
            for s in self._skills.values()
        ]

    def get_prompt_parts(self) -> list[str]:
        """获取技能列表摘要（用于初始 prompt）"""
        parts = []
        for skill in self._skills.values():
            trigger_str = ", ".join(skill.triggers) if skill.triggers else skill.name
            parts.append(
                f"- **{skill.name}** ({skill.version}): {skill.description}\n"
                f"  触发: {trigger_str}"
            )
        return parts

    def get_skill_prompt(self, name: str) -> str | None:
        """按需加载：获取技能的完整内容（含引用的文件）"""
        skill = self._skills.get(name)
        if not skill:
            return None

        skill_dir = self._dirs.get(name)
        if not skill_dir:
            return None

        parts = []

        # 读取 README.md 完整内容
        readme = skill_dir / "README.md"
        if readme.exists():
            parts.append(readme.read_text(encoding="utf-8"))

        # 读取 reference.md（如果存在）
        ref = skill_dir / "reference.md"
        if ref.exists():
            parts.append("\n\n## 参考资料\n\n" + ref.read_text(encoding="utf-8"))

        # 读取 examples.md（如果存在）
        ex = skill_dir / "examples.md"
        if ex.exists():
            parts.append("\n\n## 示例\n\n" + ex.read_text(encoding="utf-8"))

        return "\n".join(parts)

    def get_skill_allowed_tools(self, name: str) -> list[str]:
        """获取技能允许的工具列表"""
        skill = self._skills.get(name)
        return skill.allowed_tools if skill else []

    @property
    def skills(self) -> dict[str, Skill]:
        return self._skills