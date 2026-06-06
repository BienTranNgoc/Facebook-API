import hashlib
from datetime import datetime, timezone


def normalize_events(payload):
    events = []
    for entry in payload.get("entry", []):
        page_id = str(entry.get("id", ""))
        entry_time = entry.get("time")
        for change in entry.get("changes", []):
            field = change.get("field", "")
            value = change.get("value") or {}
            event = _normalize_change(page_id, entry_time, field, value)
            if event:
                events.append(event)
        for message in entry.get("messaging", []):
            event = _normalize_message(page_id, entry_time, message)
            if event:
                events.append(event)
    if not events and payload:
        events.append(_fallback_event(payload))
    return events


def _normalize_change(page_id, entry_time, field, value):
    item = value.get("item") or field
    if item != "comment" and not value.get("comment_id"):
        return None
    comment_id = str(value.get("comment_id") or value.get("id") or "")
    user = value.get("from") or {}
    event_id = f"comment:{comment_id}" if comment_id else _hash_payload(value)
    return {
        "event_id": event_id,
        "event_type": "comment",
        "source": "facebook",
        "page_id": page_id,
        "post_id": str(value.get("post_id", "")),
        "comment_id": comment_id,
        "message_id": "",
        "user_id": str(user.get("id") or value.get("sender_id") or ""),
        "user_name": str(user.get("name") or ""),
        "text": value.get("message") or value.get("text") or "",
        "verb": value.get("verb", ""),
        "created_at": _entry_time(entry_time),
        "raw": {"field": field, "value": value},
    }


def _normalize_message(page_id, entry_time, item):
    message = item.get("message") or {}
    sender = item.get("sender") or {}
    message_id = str(message.get("mid") or "")
    if not message_id and not message.get("text"):
        return None
    event_id = f"message:{message_id}" if message_id else _hash_payload(item)
    return {
        "event_id": event_id,
        "event_type": "message",
        "source": "facebook",
        "page_id": page_id,
        "post_id": "",
        "comment_id": "",
        "message_id": message_id,
        "user_id": str(sender.get("id") or ""),
        "user_name": "",
        "text": message.get("text") or "",
        "verb": "message",
        "created_at": _entry_time(entry_time),
        "raw": item,
    }


def _fallback_event(payload):
    return {
        "event_id": _hash_payload(payload),
        "event_type": "unknown",
        "source": "facebook",
        "page_id": "",
        "post_id": "",
        "comment_id": "",
        "message_id": "",
        "user_id": "",
        "user_name": "",
        "text": "",
        "verb": "unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": payload,
    }


def _hash_payload(payload):
    return "event:" + hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _entry_time(value):
    if value:
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            pass
    return datetime.now(timezone.utc).isoformat()
