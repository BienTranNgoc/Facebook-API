import unittest
from datetime import datetime, timezone

from normalizer import normalize_events, _entry_time


class TestNormalizer(unittest.TestCase):
    def test_normalize_comment_event(self):
        payload = {
            "entry": [
                {
                    "id": "page123",
                    "time": 1620000000,
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "verb": "add",
                                "comment_id": "comment_456",
                                "post_id": "post_789",
                                "message": "This is a test comment",
                                "from": {"id": "user1", "name": "John Doe"},
                            },
                        }
                    ],
                }
            ]
        }
        events = normalize_events(payload)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["event_type"], "comment")
        self.assertEqual(event["comment_id"], "comment_456")
        self.assertEqual(event["text"], "This is a test comment")
        self.assertEqual(event["user_id"], "user1")
        self.assertEqual(event["user_name"], "John Doe")
        self.assertEqual(event["page_id"], "page123")

    def test_normalize_message_event(self):
        payload = {
            "entry": [
                {
                    "id": "page123",
                    "time": 1620000000,
                    "messaging": [
                        {
                            "sender": {"id": "user2"},
                            "recipient": {"id": "page123"},
                            "message": {"mid": "mid.123", "text": "Hello page!"},
                        }
                    ],
                }
            ]
        }
        events = normalize_events(payload)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["event_type"], "message")
        self.assertEqual(event["message_id"], "mid.123")
        self.assertEqual(event["text"], "Hello page!")
        self.assertEqual(event["user_id"], "user2")
        self.assertEqual(event["page_id"], "page123")

    def test_fallback_event(self):
        payload = {"unknown_key": "unknown_value"}
        events = normalize_events(payload)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "unknown")
        self.assertEqual(events[0]["raw"], payload)

if __name__ == "__main__":
    unittest.main()
