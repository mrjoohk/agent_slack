import os

class SkillLoader:
    def __init__(self, base_dir: str = ".gemini/antigravity/skills"):
        self.base_dir = base_dir

    def load_skill_prompt(self, skill_name: str) -> str:
        """
        로컬 스킬 디렉토리에서 SKILL.md 파일을 읽어
        YAML Frontmatter를 제거한 본문(시스템 프롬프트)을 추출합니다.
        """
        skill_path = os.path.abspath(os.path.join(self.base_dir, skill_name, "SKILL.md"))
        if not os.path.exists(skill_path):
            raise BaseException(f"Skill '{skill_name}' not found at {skill_path}")

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()
            
            return content.strip()
        except Exception as e:
            print(f"Error parsing skill {skill_name}: {e}")
            return f"Error loading skill {skill_name}."
