import os
import unittest

os.environ.setdefault("MAX_RETRY_COUNT", "3")
os.environ.setdefault("RETRY_BACKOFF_BASE_SECONDS", "1")

from app import backoff_seconds, next_retry_payload, should_dead_letter


class RetryPolicyTests(unittest.TestCase):
    def test_backoff_is_exponential(self):
        self.assertEqual(backoff_seconds({"retry_count": 0}), 1)
        self.assertEqual(backoff_seconds({"retry_count": 1}), 2)
        self.assertEqual(backoff_seconds({"retry_count": 2}), 4)

    def test_dead_letter_after_limit(self):
        self.assertFalse(should_dead_letter({"retryable": True, "retry_count": 2}))
        self.assertTrue(should_dead_letter({"retryable": True, "retry_count": 3}))
        self.assertTrue(should_dead_letter({"retryable": False, "retry_count": 0}))

    def test_next_retry_increments_count(self):
        self.assertEqual(next_retry_payload({"retry_count": 0})["retry_count"], 1)


if __name__ == "__main__":
    unittest.main()
