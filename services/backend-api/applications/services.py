import logging
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .facebook_client import FacebookAPIError, FacebookClient
from .kafka_client import JsonKafkaProducer
from .models import EventRecord, IdempotencyKey, ProcessingError

logger = logging.getLogger(__name__)


class CommandProcessor:
    def __init__(self, facebook_client=None, producer=None):
        self.facebook = facebook_client or FacebookClient()
        self.producer = producer or JsonKafkaProducer()

    def process(self, command):
        command_id = command.get("command_id")
        if not command_id:
            raise ValueError("command_id is required")

        event_id = command.get("event_id", "")
        action = command.get("action", "noop")
        idempotency, created = self._claim_command(command_id, event_id, action)
        if not created and idempotency.status == IdempotencyKey.STATUS_SUCCESS:
            return {"status": "duplicate_skipped", "command_id": command_id}
        if not created and idempotency.status == IdempotencyKey.STATUS_SKIPPED:
            return {"status": "duplicate_skipped", "command_id": command_id}

        try:
            response = self._execute_action(command)
        except FacebookAPIError as exc:
            self._mark_failed(idempotency, exc.as_dict())
            self._publish_failed(command, exc)
            raise
        except Exception as exc:
            self._mark_failed(idempotency, {"message": str(exc), "retryable": False})
            self._publish_unrecoverable_failed(command, exc)
            self._record_error(command, exc)
            raise

        self._mark_success(idempotency, response)
        self._update_event_status(command, action, response)
        return {"status": "processed", "command_id": command_id, "response": response}

    def _execute_action(self, command):
        action = command.get("action", "noop")
        target = command.get("target") or {}
        if action == "reply_comment":
            comment_id = target.get("comment_id") or command.get("comment_id")
            reply_text = command.get("reply_text") or command.get("message")
            if not comment_id or not reply_text:
                raise ValueError("reply_comment requires target.comment_id and reply_text")
            return self.facebook.reply_to_comment(comment_id, reply_text)
        if action == "hide_comment":
            comment_id = target.get("comment_id") or command.get("comment_id")
            if not comment_id:
                raise ValueError("hide_comment requires target.comment_id")
            return self.facebook.hide_comment(comment_id)
        if action in {"pending_review", "noop"}:
            return {"skipped": True, "reason": command.get("reason", action)}
        raise ValueError(f"unsupported action: {action}")

    def _claim_command(self, command_id, event_id, action):
        try:
            with transaction.atomic():
                return IdempotencyKey.objects.create(
                    command_id=command_id,
                    event_id=event_id,
                    action=action,
                    status=IdempotencyKey.STATUS_PROCESSING,
                ), True
        except IntegrityError:
            return IdempotencyKey.objects.get(command_id=command_id), False

    def _mark_success(self, idempotency, response):
        idempotency.status = IdempotencyKey.STATUS_SUCCESS
        idempotency.response = response or {}
        idempotency.processed_at = timezone.now()
        idempotency.save(update_fields=["status", "response", "processed_at", "updated_at"])

    def _mark_failed(self, idempotency, response):
        idempotency.status = IdempotencyKey.STATUS_FAILED
        idempotency.response = response or {}
        idempotency.save(update_fields=["status", "response", "updated_at"])

    def _publish_failed(self, command, exc):
        failed_payload = dict(command)
        failed_payload["retry_count"] = int(command.get("retry_count", 0))
        failed_payload["retryable"] = exc.retryable
        failed_payload["last_error"] = exc.as_dict()
        self.producer.publish(
            settings.KAFKA_SEND_FAILED_TOPIC,
            failed_payload,
            key=failed_payload.get("command_id"),
        )
        ProcessingError.objects.create(
            event_id=failed_payload.get("event_id", ""),
            command_id=failed_payload.get("command_id", ""),
            topic=settings.KAFKA_SEND_FAILED_TOPIC,
            retry_count=failed_payload.get("retry_count", 0),
            error_type="FacebookAPIError",
            error_message=exc.message,
            payload=failed_payload,
        )

    def _publish_unrecoverable_failed(self, command, exc):
        failed_payload = dict(command)
        failed_payload["retry_count"] = int(command.get("retry_count", 0))
        failed_payload["retryable"] = False
        failed_payload["last_error"] = {
            "message": str(exc),
            "type": exc.__class__.__name__,
            "retryable": False,
        }
        self.producer.publish(
            settings.KAFKA_SEND_FAILED_TOPIC,
            failed_payload,
            key=failed_payload.get("command_id"),
        )

    def _record_error(self, command, exc):
        ProcessingError.objects.create(
            event_id=command.get("event_id", ""),
            command_id=command.get("command_id", ""),
            retry_count=int(command.get("retry_count", 0)),
            error_type=exc.__class__.__name__,
            error_message=str(exc),
            payload=command,
        )

    def _update_event_status(self, command, action, response):
        event_id = command.get("event_id")
        if not event_id:
            return
        status = EventRecord.STATUS_REPLIED if action == "reply_comment" else EventRecord.STATUS_PROCESSED
        if action == "pending_review":
            status = EventRecord.STATUS_PENDING_REVIEW
        EventRecord.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": command.get("event_type", "comment"),
                "facebook_user_id": (command.get("target") or {}).get("user_id", ""),
                "post_id": (command.get("target") or {}).get("post_id", ""),
                "comment_id": (command.get("target") or {}).get("comment_id", ""),
                "message_id": (command.get("target") or {}).get("message_id", ""),
                "message": command.get("source_text", ""),
                "intent": command.get("intent", ""),
                "sentiment": command.get("sentiment", ""),
                "action": action,
                "status": status,
                "payload": {"command": command, "facebook_response": response},
            },
        )
