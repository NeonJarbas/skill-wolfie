import unittest
from ovos_plugin_manager.skills import find_skill_plugins
from skill_wolfie import WolframAlphaSkill


class TestPlugin(unittest.TestCase):
    def test_skill_id(self):
        setup_skill_id = "skill-wolfie.jarbasai"
        plugs = find_skill_plugins()
        self.assertTrue(setup_skill_id in plugs)
        self.assertEqual(plugs[setup_skill_id], WolframAlphaSkill)
