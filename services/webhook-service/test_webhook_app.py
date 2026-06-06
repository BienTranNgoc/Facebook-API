import json
import unittest
from unittest.mock import MagicMock
from app import Handler

class TestApp(unittest.TestCase):
    def test_health_check(self):
        handler = MagicMock(spec=Handler)
        handler.path = "/health"
        
        # Use a real instance method but with a mock self
        Handler.do_GET(handler)
        
        handler._json.assert_called_with(200, {"ok": True, "service": "webhook-service"})

if __name__ == "__main__":
    unittest.main()
