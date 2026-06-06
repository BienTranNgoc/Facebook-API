import unittest
from ai import Analyzer, _parse_bool, _parse_confidence

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

    def test_parse_gemini_confidence_labels(self):
        self.assertEqual(_parse_confidence("high"), 0.9)
        self.assertEqual(_parse_confidence("85%"), 0.85)
        self.assertEqual(_parse_confidence("unexpected"), 0.5)
        self.assertTrue(_parse_bool("true"))
        self.assertFalse(_parse_bool("false"))

if __name__ == "__main__":
    unittest.main()
