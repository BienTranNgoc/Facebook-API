import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kafka_client import JsonKafkaConsumer, JsonKafkaProducer

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("retry-service")

PORT = int(os.getenv("PORT", "3003"))
SEND_FAILED_TOPIC = os.getenv("KAFKA_SEND_FAILED_TOPIC", "send_failed")
SEND_RETRY_TOPIC = os.getenv("KAFKA_SEND_RETRY_TOPIC", "send_retry")
DEAD_LETTER_TOPIC = os.getenv("KAFKA_DEAD_LETTER_TOPIC", "dead_letter")
MAX_RETRIES = int(os.getenv("MAX_RETRY_COUNT", "3"))
BACKOFF_BASE_SECONDS = float(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "1"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"ok": True, "service": "retry-service"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.info(fmt, *args)


def start_health_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


def next_retry_payload(payload):
    retry_count = int(payload.get("retry_count", 0))
    next_payload = dict(payload)
    next_payload["retry_count"] = retry_count + 1
    next_payload["scheduled_at"] = datetime.now(timezone.utc).isoformat()
    return next_payload


def should_dead_letter(payload):
    retryable = bool(payload.get("retryable", True))
    retry_count = int(payload.get("retry_count", 0))
    return (not retryable) or retry_count >= MAX_RETRIES


def backoff_seconds(payload):
    retry_count = int(payload.get("retry_count", 0))
    return BACKOFF_BASE_SECONDS * (2 ** retry_count)


def run_consumer():
    consumer = JsonKafkaConsumer([SEND_FAILED_TOPIC], group_id="retry-service")
    producer = JsonKafkaProducer()
    logger.info("retry-service consuming topic=%s", SEND_FAILED_TOPIC)
    for message in consumer:
        payload = message.value
        command_id = payload.get("command_id")
        try:
            if should_dead_letter(payload):
                dead = dict(payload)
                dead["dead_lettered_at"] = datetime.now(timezone.utc).isoformat()
                dead["dead_letter_reason"] = "non_retryable_or_retry_limit_reached"
                producer.publish(DEAD_LETTER_TOPIC, dead, key=command_id)
                logger.error("command sent to dead_letter command_id=%s", command_id)
            else:
                delay = backoff_seconds(payload)
                logger.info("retry scheduled command_id=%s delay=%ss", command_id, delay)
                time.sleep(delay)
                retry_payload = next_retry_payload(payload)
                producer.publish(SEND_RETRY_TOPIC, retry_payload, key=command_id)
        except Exception:
            logger.exception("failed to process retry message")
        finally:
            consumer.commit()


if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    run_consumer()
