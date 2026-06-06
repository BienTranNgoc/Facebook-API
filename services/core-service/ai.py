import json
import logging
import os
import re
import unicodedata
import urllib.error
import urllib.request

from circuit_breaker import CircuitBreaker, CircuitOpen

logger = logging.getLogger(__name__)

_LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_REPEAT_RE = re.compile(r"(.{4,}?)\1{2,}", re.IGNORECASE)


class Analyzer:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "8"))
        self.breaker = CircuitBreaker(
            "ai-api",
            failure_threshold=int(os.getenv("AI_CIRCUIT_FAILURE_THRESHOLD", "5")),
            recovery_seconds=int(os.getenv("AI_CIRCUIT_RECOVERY_SECONDS", "30")),
        )

    def analyze(self, event):
        text = event.get("text", "")
        if not self.gemini_key:
            return self.heuristic(text)
        try:
            self.breaker.before_call()
            result = self._call_gemini(text)
            self.breaker.record_success()
            return result
        except (CircuitOpen, TimeoutError, urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
            self.breaker.record_failure()
            logger.warning("gemini analysis failed; using heuristic fallback: %s", exc)
            fallback = self.heuristic(text)
            fallback["provider"] = "heuristic_fallback"
            return fallback

    def heuristic(self, text):
        normalized = _normalize(text)
        is_spam = bool(_LINK_RE.search(text)) or bool(_REPEAT_RE.search(normalized))
        if any(word in normalized for word in ["scam", "link", "kiem tien", "vay tien", "casino"]):
            is_spam = True
        if is_spam:
            return {
                "intent": "spam",
                "sentiment": "negative",
                "spam": True,
                "confidence": 0.95,
                "provider": "heuristic",
            }
        if any(word in normalized for word in ["gia", "bao nhieu", "price", "mua", "dat hang"]):
            return {
                "intent": "ask_price",
                "sentiment": "neutral",
                "spam": False,
                "confidence": 0.8,
                "provider": "heuristic",
            }
        if any(word in normalized for word in ["tot", "hay", "cam on", "ung ho", "tuyet", "nhanh", "hai long"]):
            return {
                "intent": "praise",
                "sentiment": "positive",
                "spam": False,
                "confidence": 0.78,
                "provider": "heuristic",
            }
        if any(word in normalized for word in ["khieu nai", "chua nhan", "tre", "loi", "te", "that vong"]):
            return {
                "intent": "complaint",
                "sentiment": "negative",
                "spam": False,
                "confidence": 0.82,
                "provider": "heuristic",
            }
        return {"intent": "general", "sentiment": "neutral", "spam": False, "confidence": 0.6, "provider": "heuristic"}

    def _call_gemini(self, text):
        prompt = (
            "Analyze this Facebook Page comment and draft a page reply. Return strict JSON with keys: "
            "intent, sentiment, spam, confidence, reply_text. sentiment must be 'positive', 'neutral', or 'negative'. "
            "reply_text must be natural Vietnamese, friendly, no hashtags, no markdown, at most 250 characters. "
            "If spam is true or no public reply is appropriate, set reply_text to an empty string. "
            "Do not invent prices, policies, discounts, order status, or private details. Do not mention AI."
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={self.gemini_key}"
        )
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt + "\n\nComment: " + text[:1500]}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        content = payload["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(content)

        return {
            "intent": result.get("intent", "general"),
            "sentiment": result.get("sentiment", "neutral"),
            "spam": _parse_bool(result.get("spam", False)),
            "confidence": _parse_confidence(result.get("confidence", 0.5)),
            "reply_text": _clean_reply(result.get("reply_text", "")),
            "provider": "gemini",
        }


def _normalize(text):
    folded = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return ascii_text.lower()


def _clean_reply(value):
    text = str(value or "").strip()
    text = " ".join(text.split())
    return text[:500]


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "spam"}


def _parse_confidence(value):
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value or "").strip().lower()
    labels = {
        "very high": 0.95,
        "high": 0.9,
        "medium": 0.6,
        "moderate": 0.6,
        "low": 0.3,
    }
    if text in labels:
        return labels[text]
    try:
        parsed = float(text.rstrip("%"))
    except ValueError:
        return 0.5
    if parsed > 1:
        parsed = parsed / 100
    return max(0.0, min(1.0, parsed))
