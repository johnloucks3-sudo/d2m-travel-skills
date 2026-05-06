import importlib
import logging
from pathlib import Path

class SkillRegistry:
    def __init__(self):
        self.skills = {}
        self.skill_dir = Path("/home/john/Thunderbird/core/skills")
    
    def register_skill(self, skill_name: str):
        module = importlib.import_module(f"core.skills.{skill_name}")
        self.skills[skill_name] = module
        logging.info(f"Skill {skill_name} registered.")
