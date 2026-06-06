import json
import os
import re
import unicodedata
import urllib.error
import urllib.request

from circuit_breaker import CircuitBreaker, CircuitOpen

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
        except (CircuitOpen, TimeoutError, urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as e:
            self.breaker.record_failure()
            fallback = self.heuristic(text)
            fallback["provider"] = "heuristic_fallback"
            return fallback

    def heuristic(self, text):
        normalized = _normalize(text)
        is_spam = bool(_LINK_RE.search(text)) or bool(_REPEAT_RE.search(normalized))
        if any(word in normalized for word in ["scam", "link", "kiem tien", "vay tien", "casino"]):
            is_spam = True
        if is_spam:
            return {"intent": "spam", "sentiment": "negative", "spam": True, "confidence": 0.95, "provider": "heuristic"}
        if any(word in normalized for word in ["gia", "bao nhieu", "price", "mua", "dat hang"]):
            return {"intent": "ask_price", "sentiment": "neutral", "spam": False, "confidence": 0.8, "provider": "heuristic"}
        if any(word in normalized for word in ["khieu nai", "chua nhan", "tre", "loi", "te", "that vong", "ho tro"]):
            return {"intent": "complaint", "sentiment": "negative", "spam": False, "confidence": 0.82, "provider": "heuristic"}
        if any(word in normalized for word in ["tot", "hay", "cam on", "ung ho", "tuyet", "nhanh"]):
            return {"intent": "praise", "sentiment": "positive", "spam": False, "confidence": 0.78, "provider": "heuristic"}
        return {"intent": "general", "sentiment": "neutral", "spam": False, "confidence": 0.6, "provider": "heuristic"}

    def _call_gemini(self, text):
        prompt = (
            "Classify this Facebook Page comment. Return strict JSON with keys: "
            "intent, sentiment, spam, confidence. sentiment must be 'positive', 'neutral', or 'negative'."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        body = json.dumps(
            {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt + "\n\nComment: " + text[:1500]}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json"
                }
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
            "spam": bool(result.get("spam", False)),
            "confidence": float(result.get("confidence", 0.5)),
            "provider": "gemini",
        }


def _normalize(text):
    folded = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return ascii_text.lower()
