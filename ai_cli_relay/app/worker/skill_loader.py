from pathlib import Path


class SkillLoader:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = str(Path.home() / ".gemini" / "antigravity" / "skills")
        self.base_dir = Path(base_dir)

    def load_skill_prompt(self, skill_name: str) -> str:
        """
        로컬 스킬 디렉토리에서 SKILL.md 파일을 읽어
        YAML Frontmatter를 제거한 본문(시스템 프롬프트)을 추출합니다.
        """
        skill_path = (self.base_dir / skill_name / "SKILL.md").resolve()

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill '{skill_name}' not found at {skill_path}")

        try:
            content = skill_path.read_text(encoding='utf-8')

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()

            return content.strip()
        except Exception as e:
            print(f"Error parsing skill {skill_name}: {e}")
            return f"Error loading skill {skill_name}."
