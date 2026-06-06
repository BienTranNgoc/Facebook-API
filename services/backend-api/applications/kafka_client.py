import json
import logging
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaUnavailable(RuntimeError):
    pass


class JsonKafkaProducer:
    def __init__(self):
        self.enabled = settings.KAFKA_ENABLED
        self._producer = None
        if not self.enabled:
            return
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise KafkaUnavailable("kafka-python is not installed") from exc
        self._producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda value: json.dumps(value, ensure_ascii=True).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value else None,
            acks="all",
            retries=3,
        )

    def publish(self, topic, payload, key=None):
        if not self.enabled:
            logger.info("Kafka disabled; skip publish topic=%s payload=%s", topic, payload)
            return None
        future = self._producer.send(topic, value=payload, key=key)
        metadata = future.get(timeout=10)
        self._producer.flush(timeout=10)
        return {"topic": metadata.topic, "partition": metadata.partition, "offset": metadata.offset}


class JsonKafkaConsumer:
    def __init__(self, topics: Iterable[str], group_id: str):
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise KafkaUnavailable("kafka-python is not installed") from exc
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            key_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
        )

    def __iter__(self):
        return iter(self.consumer)

    def commit(self):
        self.consumer.commit()
