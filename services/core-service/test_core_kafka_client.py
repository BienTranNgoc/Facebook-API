import unittest

from kafka_client import safe_json_deserializer


class KafkaClientTests(unittest.TestCase):
    def test_safe_json_deserializer_returns_dict_for_object(self):
        self.assertEqual(safe_json_deserializer(b'{"event_id":"event-1"}'), {"event_id": "event-1"})

    def test_safe_json_deserializer_marks_invalid_json(self):
        result = safe_json_deserializer(b'"event_id": "event-1"')

        self.assertTrue(result["_malformed_json"])
        self.assertIn("Extra data", result["_error"])
        self.assertIn("event-1", result["_raw"])

    def test_safe_json_deserializer_allows_non_object_json(self):
        self.assertEqual(safe_json_deserializer(b'"event-1"'), "event-1")

    def test_safe_json_deserializer_parses_double_encoded_object(self):
        result = safe_json_deserializer(b'"{\\"event_id\\": \\"event-1\\"}"')

        self.assertEqual(result, {"event_id": "event-1"})


if __name__ == "__main__":
    unittest.main()
