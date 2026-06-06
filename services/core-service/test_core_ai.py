import json
import unittest
from unittest.mock import MagicMock, patch

from ai import Analyzer


class TestAI(unittest.TestCase):
    def setUp(self):
        self.analyzer = Analyzer()
        # Ensure heuristic mode for testing
        self.analyzer.gemini_key = ""

    def test_heuristic_spam(self):
        result = self.analyzer.analyze({"text": "kiem tien nhanh nhat o day https://example.com"})
        self.assertEqual(result["intent"], "spam")
        self.assertEqual(result["sentiment"], "negative")
        self.assertTrue(result["spam"])

    def test_heuristic_ask_price(self):
        result = self.analyzer.analyze({"text": "Cho hoi gia bao nhieu vay shop?"})
        self.assertEqual(result["intent"], "ask_price")
        self.assertEqual(result["sentiment"], "neutral")
        self.assertFalse(result["spam"])

    def test_heuristic_complaint(self):
        result = self.analyzer.analyze({"text": "Minh chua nhan duoc hang, dich vu qua te!"})
        self.assertEqual(result["intent"], "complaint")
        self.assertEqual(result["sentiment"], "negative")
        self.assertFalse(result["spam"])

    def test_heuristic_praise(self):
        result = self.analyzer.analyze({"text": "San pham rat tot, cam on shop!"})
        self.assertEqual(result["intent"], "praise")
        self.assertEqual(result["sentiment"], "positive")
        self.assertFalse(result["spam"])

    def test_heuristic_praise_with_support_word(self):
        result = self.analyzer.analyze({"text": "Shop ho tro rat nhanh, minh rat hai long"})
        self.assertEqual(result["intent"], "praise")
        self.assertEqual(result["sentiment"], "positive")
        self.assertFalse(result["spam"])

    @patch("urllib.request.urlopen")
    def test_call_gemini_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"intent": "praise", "sentiment": "positive", "spam": false, '
                                        '"confidence": 0.9, "reply_text": "Cam on ban!"}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.analyzer.gemini_key = "fake-key"
        result = self.analyzer.analyze({"text": "Great service!"})

        self.assertEqual(result["intent"], "praise")
        self.assertEqual(result["sentiment"], "positive")
        self.assertEqual(result["provider"], "gemini")

    @patch("urllib.request.urlopen")
    def test_call_gemini_failure_triggers_fallback(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("API Down")

        self.analyzer.gemini_key = "fake-key"
        result = self.analyzer.analyze({"text": "Kiem tien nhanh"})

        self.assertEqual(result["provider"], "heuristic_fallback")
        self.assertEqual(result["intent"], "spam")


if __name__ == "__main__":
    unittest.main()
