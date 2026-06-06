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

    def test_rate_limiting_works(self):
        engine = AutomationEngine()
        user_id = "spammer-1"
        analysis = {"sentiment": "neutral", "spam": False}

        # Fire 20 events
        for i in range(20):
            engine.decide({"user_id": user_id, "event_id": f"evt-{i}"}, analysis)

        # 21st event should be rate limited
        command = engine.decide({"user_id": user_id, "event_id": "evt-21"}, analysis)
        self.assertEqual(command["action"], "pending_review")
        self.assertEqual(command["reason"], "rate_limit")

    def test_spam_tracking_works(self):
        engine = AutomationEngine()
        user_id = "spammer-2"
        analysis = {"sentiment": "negative", "spam": True}

        # 1st and 2nd spam
        engine.decide({"user_id": user_id, "event_id": "s1"}, analysis)
        engine.decide({"user_id": user_id, "event_id": "s2"}, analysis)

        # 3rd spam should be marked as spam_repeated
        command = engine.decide({"user_id": user_id, "event_id": "s3"}, analysis)
        self.assertEqual(command["action"], "hide_comment")
        self.assertEqual(command["reason"], "spam_repeated")

    def test_complaint_and_ask_price_replies(self):
        engine = AutomationEngine()

        # Complaint
        cmd1 = engine.decide({"event_id": "e1"}, {"sentiment": "negative", "intent": "complaint"})
        self.assertEqual(cmd1["action"], "reply_comment")
        self.assertIn("xin loi", cmd1["reply_text"])

        # Ask Price
        cmd2 = engine.decide({"event_id": "e2"}, {"sentiment": "neutral", "intent": "ask_price"})
        self.assertEqual(cmd2["action"], "reply_comment")
        self.assertIn("Admin se gui", cmd2["reply_text"])


if __name__ == "__main__":
    unittest.main()
