from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class AutomationEngine:
    def __init__(self):
        self.user_events = defaultdict(deque)
        self.spam_events = defaultdict(deque)

    def decide(self, event, analysis):
        now = datetime.now(timezone.utc)
        if self._rate_limited(event.get("user_id", ""), now):
            return self._command(event, analysis, "pending_review", reason="rate_limit")

        if analysis.get("spam") or analysis.get("intent") == "spam":
            repeated = self._track_spam(event.get("user_id", ""), now) >= 3
            reason = "spam_repeated" if repeated else "spam"
            return self._command(event, analysis, "hide_comment", reason=reason)

        sentiment = analysis.get("sentiment", "neutral")
        intent = analysis.get("intent", "general")
        if sentiment == "positive":
            return self._command(event, analysis, "reply_comment", reply_text="Cam on ban da ung ho page!", reason="positive_sentiment")
        if sentiment == "negative":
            return self._command(event, analysis, "reply_comment", reply_text="Rat xin loi ve trai nghiem chua tot. Ben minh se kiem tra va ho tro ngay.", reason="negative_sentiment")
        if intent == "ask_price":
            return self._command(event, analysis, "reply_comment", reply_text="Cam on ban da quan tam. Admin se gui thong tin chi tiet som nhat.", reason="ask_price")
        return self._command(event, analysis, "noop", reason="no_automation_rule")

    def _rate_limited(self, user_id, now):
        if not user_id:
            return False
        window = self.user_events[user_id]
        cutoff = now - timedelta(minutes=1)
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)
        return len(window) > 20

    def _track_spam(self, user_id, now):
        if not user_id:
            return 1
        window = self.spam_events[user_id]
        cutoff = now - timedelta(hours=24)
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)
        return len(window)

    def _command(self, event, analysis, action, reply_text="", reason=""):
        target = {
            "page_id": event.get("page_id", ""),
            "post_id": event.get("post_id", ""),
            "comment_id": event.get("comment_id", ""),
            "message_id": event.get("message_id", ""),
            "user_id": event.get("user_id", ""),
        }
        return {
            "command_id": str(uuid4()),
            "event_id": event.get("event_id", ""),
            "event_type": event.get("event_type", "comment"),
            "action": action,
            "target": target,
            "reply_text": reply_text,
            "reason": reason,
            "intent": analysis.get("intent", "general"),
            "sentiment": analysis.get("sentiment", "neutral"),
            "spam": bool(analysis.get("spam", False)),
            "confidence": analysis.get("confidence", 0),
            "source_text": event.get("text", ""),
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "raw_event": event,
        }
