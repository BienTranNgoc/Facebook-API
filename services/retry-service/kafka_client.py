import json
import logging
import os

logger = logging.getLogger(__name__)


def bootstrap_servers():
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")


class JsonKafkaProducer:
    def __init__(self):
        self.enabled = os.getenv("KAFKA_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        self._producer = None
        if not self.enabled:
            return
        from kafka import KafkaProducer

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers(),
            value_serializer=lambda value: json.dumps(value, ensure_ascii=True).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value else None,
            acks="all",
            retries=3,
        )

    def publish(self, topic, payload, key=None):
        if not self.enabled:
            logger.info("Kafka disabled; topic=%s payload=%s", topic, payload)
            return None
        future = self._producer.send(topic, value=payload, key=key)
        metadata = future.get(timeout=10)
        self._producer.flush(timeout=10)
        return {"topic": metadata.topic, "partition": metadata.partition, "offset": metadata.offset}


class JsonKafkaConsumer:
    def __init__(self, topics, group_id):
        from kafka import KafkaConsumer

        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers(),
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
