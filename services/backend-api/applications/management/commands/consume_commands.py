import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from applications.facebook_client import FacebookAPIError
from applications.kafka_client import JsonKafkaConsumer, KafkaUnavailable
from applications.services import CommandProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume reply_commands and send_retry topics, then call Facebook Graph API idempotently."

    def handle(self, *args, **options):
        topics = [settings.KAFKA_REPLY_COMMANDS_TOPIC, settings.KAFKA_SEND_RETRY_TOPIC]
        self.stdout.write(f"backend-api consuming topics: {', '.join(topics)}")
        try:
            consumer = JsonKafkaConsumer(topics, group_id="backend-api")
        except KafkaUnavailable as exc:
            raise SystemExit(str(exc)) from exc

        processor = CommandProcessor()
        for message in consumer:
            payload = message.value
            try:
                result = processor.process(payload)
                logger.info(
                    "command processed command_id=%s action=%s status=%s",
                    payload.get("command_id", ""),
                    payload.get("action", ""),
                    result.get("status", "processed"),
                )
            except FacebookAPIError as exc:
                logger.warning("facebook command failed and was published to retry pipeline: %s", exc.message)
            except Exception:
                logger.exception("unexpected command processing failure")
            finally:
                consumer.commit()
