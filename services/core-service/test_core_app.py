import json
import unittest
from unittest.mock import MagicMock
from app import HealthHandler

class TestApp(unittest.TestCase):
    def test_health_check(self):
        handler = MagicMock(spec=HealthHandler)
        handler.path = "/health"
        handler.wfile = MagicMock()
        
        # Use a real instance method but with a mock self
        HealthHandler.do_GET(handler)
        
        handler.send_response.assert_called_with(200)
        # Check if "core-service" is in the response
        args, _ = handler.wfile.write.call_args
        response_body = json.loads(args[0].decode("utf-8"))
        self.assertEqual(response_body["service"], "core-service")

if __name__ == "__main__":
    unittest.main()
