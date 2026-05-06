import unittest
from core.ai_infra.thunderbird_skill_builder import SkillBuilder
from core.mcp.skill_registry import SkillRegistry

class TestOpenClawP0(unittest.TestCase):
    def test_skill_builder_and_registry(self):
        builder = SkillBuilder()
        builder.build_from_description("Test tool", "test_skill")
        registry = SkillRegistry()
        registry.register_skill("test_skill")
        self.assertIn("test_skill", registry.skills)

if __name__ == "__main__":
    unittest.main()
