import unittest

from automation import AutomationEngine


class AutomationEngineTests(unittest.TestCase):
    def test_self_page_comment_is_ignored(self):
        engine = AutomationEngine()
        event = {
            "event_id": "comment:self",
            "event_type": "comment",
            "page_id": "page-1",
            "user_id": "page-1",
            "comment_id": "comment-1",
            "text": "Rat xin loi ve trai nghiem chua tot.",
        }

        self.assertTrue(engine.should_ignore(event))
        command = engine.decide(event, {"sentiment": "negative", "intent": "complaint"})

        self.assertEqual(command["action"], "noop")
        self.assertEqual(command["reason"], "self_event")
        self.assertEqual(command["intent"], "ignored")

    def test_customer_positive_comment_still_replies(self):
        engine = AutomationEngine()
        event = {
            "event_id": "comment:customer",
            "event_type": "comment",
            "page_id": "page-1",
            "user_id": "user-1",
            "comment_id": "comment-2",
            "text": "Rat tot",
        }

        command = engine.decide(event, {"sentiment": "positive", "intent": "praise"})

        self.assertEqual(command["action"], "reply_comment")
        self.assertEqual(command["reason"], "positive_sentiment")

    def test_customer_positive_comment_uses_ai_reply_text(self):
        engine = AutomationEngine()
        event = {
            "event_id": "comment:customer-ai",
            "event_type": "comment",
            "page_id": "page-1",
            "user_id": "user-1",
            "comment_id": "comment-3",
            "text": "Shop tu van rat nhiet tinh",
        }

        command = engine.decide(
            event,
            {
                "sentiment": "positive",
                "intent": "praise",
                "reply_text": "Cam on ban da ghi nhan, shop rat vui khi duoc ho tro ban!",
                "provider": "gemini",
            },
        )

        self.assertEqual(command["action"], "reply_comment")
        self.assertEqual(command["reply_text"], "Cam on ban da ghi nhan, shop rat vui khi duoc ho tro ban!")
        self.assertEqual(command["analysis_provider"], "gemini")


if __name__ == "__main__":
    unittest.main()
