import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai import Analyzer
from automation import AutomationEngine
from dedup import DedupStore
from kafka_client import JsonKafkaConsumer, JsonKafkaProducer

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("core-service")

PORT = int(os.getenv("PORT", "3002"))
RAW_EVENTS_TOPIC = os.getenv("KAFKA_RAW_EVENTS_TOPIC", "raw_events")
REPLY_COMMANDS_TOPIC = os.getenv("KAFKA_REPLY_COMMANDS_TOPIC", "reply_commands")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"ok": True, "service": "core-service"}).encode("utf-8")
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


def run_consumer():
    dedup = DedupStore()
    analyzer = Analyzer()
    engine = AutomationEngine()
    producer = JsonKafkaProducer()
    consumer = JsonKafkaConsumer([RAW_EVENTS_TOPIC], group_id="core-service")
    logger.info("core-service consuming topic=%s", RAW_EVENTS_TOPIC)
    for message in consumer:
        event = message.value
        event_id = event.get("event_id")
        should_commit = False
        try:
            if not event_id:
                logger.warning("skip event without event_id: %s", event)
                should_commit = True
                continue
            if dedup.seen(event_id):
                logger.info("duplicate event skipped event_id=%s", event_id)
                should_commit = True
                continue
            analysis = analyzer.analyze(event)
            command = engine.decide(event, analysis)
            producer.publish(REPLY_COMMANDS_TOPIC, command, key=command["command_id"])
            dedup.mark_processed(event_id)
            should_commit = True
            logger.info("event processed event_id=%s action=%s", event_id, command["action"])
        except Exception:
            logger.exception("failed to process raw event; offset will not be committed")
        finally:
            if should_commit:
                consumer.commit()


if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    run_consumer()
