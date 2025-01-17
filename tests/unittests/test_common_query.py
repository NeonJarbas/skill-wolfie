import json
import unittest
from unittest.mock import Mock
from mycroft.skills import FallbackSkill
from ovos_skill_common_query import QuestionsAnswersSkill
from ovos_utils.messagebus import FakeBus, Message
from skill_wolfie import WolframAlphaSkill


class TestCommonQuery(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.bus.emitted_msgs = []

        def get_msg(msg):
            self.bus.emitted_msgs.append(json.loads(msg))

        self.skill = WolframAlphaSkill()
        self.skill._startup(self.bus, "wolfie.test")
        self.skill.wolfie.long_answer = Mock()
        self.skill.wolfie.long_answer.return_value = [
            {"title": "wolfie skill", "summary": "the answer is always 42"}]

        # after wolfram to only get common_query messages
        self.bus.on("message", get_msg)

        self.cc = QuestionsAnswersSkill()
        self.cc._startup(self.bus, "common_query.test")

    def test_skill_id(self):
        self.assertEqual(self.cc.skill_id, "common_query.test")

        # if running in ovos-core every message will have the skill_id in context
        for msg in self.bus.emitted_msgs:
            self.assertEqual(msg["context"]["skill_id"], "common_query.test")

    def test_intent_register(self):
        # helper .voc files only, no intents
        self.assertTrue(isinstance(self.cc, FallbackSkill))

        adapt_ents = ["common_query_testQuestion"]
        for msg in self.bus.emitted_msgs:
            if msg["type"] == "register_vocab":
                self.assertTrue(msg["data"]["entity_type"] in adapt_ents)

    def test_registered_events(self):
        registered_events = [e[0] for e in self.cc.events]

        # common query event handlers
        common_query = ['question:query.response']
        for event in common_query:
            self.assertTrue(event in registered_events)

        # base skill class events shared with mycroft-core
        default_skill = ["mycroft.skill.enable_intent",
                         "mycroft.skill.disable_intent",
                         "mycroft.skill.set_cross_context",
                         "mycroft.skill.remove_cross_context",
                         "intent.service.skills.deactivated",
                         "intent.service.skills.activated",
                         "mycroft.skills.settings.changed"]
        for event in default_skill:
            self.assertTrue(event in registered_events)

        # base skill class events exclusive to ovos-core
        default_ovos = ["skill.converse.ping",
                        "skill.converse.request",
                        f"{self.cc.skill_id}.activate",
                        f"{self.cc.skill_id}.deactivate"]
        for event in default_ovos:
            self.assertTrue(event in registered_events)

    def test_common_query_events(self):
        self.bus.emitted_msgs = []
        self.cc.handle_question(Message("fallback_cycle_test",
                                        {"utterance": "what is the speed of light"},
                                        {"source": "unittests",
                                         "destination": "common_query"}))

        query_messages = [
            # thinking animation
            {'type': 'enclosure.mouth.think',
             'data': {},
             'context': {'destination': ['enclosure'],
                         'skill_id': 'common_query.test'}},
            # send query
            {'type': 'question:query',
             'data': {'phrase': 'what is the speed of light'},
             'context': {'destination': 'unittests',
                         'skill_id': 'common_query.test',
                         'source': 'common_query'}},

            # skill announces its searching
            {'type': 'question:query.response',
             'data': {'phrase': 'what is the speed of light',
                      'skill_id': 'wolfie.test',
                      'searching': True},
             'context': {'skill_id': 'wolfie.test',
                         'destination': 'unittests',
                         'source': 'common_query'}},
        ]

        answer_messages = [
            # skill context set by wolfram alpha skill for continuous dialog
            {'type': 'add_context',
             'data': {'context': 'wolfie_testWolfieKnows',
                      'word': 'what is the speed of light',
                      'origin': ''},
             'context': {'destination': 'unittests',
                         'skill_id': 'common_query.test',
                         'source': 'common_query'}},
            # final wolfram response
            {'type': 'question:query.response',
             'data': {'phrase': 'what is the speed of light',
                      'skill_id': 'wolfie.test',
                      'answer': "the answer is always 42",
                      'callback_data': {'query': 'what is the speed of light',
                                        'answer': "the answer is always 42"},
                      'conf': 0.0},
             'context': {'destination': 'unittests',
                         'skill_id': 'common_query.test',
                         'source': 'common_query'}},

        ]
        timeout_extensions = ['mycroft.scheduler.schedule_event',
                              'mycroft.scheduler.remove_event']

        ctr = 0
        msgs = query_messages + answer_messages
        for msg in self.bus.emitted_msgs:
            if msg["type"] in timeout_extensions:
                # ignore timeouts, message order not assured
                continue

            # ignore conf value, we are not testing that
            if msg["data"].get("conf"):
                msg["data"]["conf"] = 0.0
            self.assertEqual(msg, msgs[ctr])
            ctr += 1
