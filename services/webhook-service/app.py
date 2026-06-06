import hashlib
import hmac
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from kafka_client import JsonKafkaProducer
from normalizer import normalize_events

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("webhook-service")

PORT = int(os.getenv("PORT", "3001"))
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "local-verify-token")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
REQUIRE_SIGNATURE = os.getenv("REQUIRE_WEBHOOK_SIGNATURE", "false").lower() in {"1", "true", "yes", "on"}
RAW_EVENTS_TOPIC = os.getenv("KAFKA_RAW_EVENTS_TOPIC", "raw_events")
producer = JsonKafkaProducer()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True, "service": "webhook-service"})
            return
        if parsed.path != "/webhook":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        query = parse_qs(parsed.query)
        mode = (query.get("hub.mode") or [""])[0]
        token = (query.get("hub.verify_token") or [""])[0]
        challenge = (query.get("hub.challenge") or [""])[0]
        if mode == "subscribe" and token == VERIFY_TOKEN:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return
        self._json(403, {"ok": False, "error": "invalid_verify_token"})

    def do_POST(self):
        if urlparse(self.path).path != "/webhook":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        if not verify_signature(raw_body, self.headers.get("X-Hub-Signature-256", "")):
            self._json(403, {"ok": False, "error": "invalid_signature"})
            return
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid_json"})
            return
        try:
            events = normalize_events(payload)
            published = []
            for event in events:
                metadata = producer.publish(RAW_EVENTS_TOPIC, event, key=event.get("event_id"))
                published.append({"event_id": event.get("event_id"), "metadata": metadata})
            self._json(200, {"ok": True, "published": published})
        except Exception as exc:
            logger.exception("failed to publish webhook event")
            self._json(500, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        logger.info("%s - %s", self.address_string(), fmt % args)

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def verify_signature(raw_body, signature):
    if not APP_SECRET:
        return not REQUIRE_SIGNATURE
    expected = "sha256=" + hmac.new(APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    logger.info("webhook-service listening on port %s", PORT)
    server.serve_forever()
