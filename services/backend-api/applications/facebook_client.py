import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings

from .circuit_breaker import CircuitBreaker, CircuitOpen
from .models import FacebookRequestLog

logger = logging.getLogger(__name__)
FACEBOOK_DUPLICATE_SPAM_MARK_SUBCODE = 1446036
facebook_breaker = CircuitBreaker(
    "facebook-api",
    failure_threshold=settings.FACEBOOK_CIRCUIT_FAILURE_THRESHOLD,
    recovery_seconds=settings.FACEBOOK_CIRCUIT_RECOVERY_SECONDS,
)


@dataclass
class FacebookAPIError(Exception):
    message: str
    status_code: int = 500
    retryable: bool = False
    response: dict | None = None

    def as_dict(self):
        return {
            "message": self.message,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "response": self.response or {},
        }


class FacebookClient:
    def __init__(self):
        self.graph_version = settings.FACEBOOK_GRAPH_VERSION
        self.page_id = settings.FACEBOOK_PAGE_ID
        self.page_access_token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
        self.timeout = settings.FACEBOOK_REQUEST_TIMEOUT_SECONDS
        self.mock_mode = settings.FACEBOOK_API_MODE == "mock"
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

    def list_posts(self, limit=25):
        if self.mock_mode:
            return {
                "data": [
                    {
                        "id": "mock_post_1",
                        "message": "Demo post from backend-api mock mode",
                        "created_time": "2026-06-05T00:00:00+0000",
                    }
                ]
            }
        self._require_token()
        return self._request("GET", f"/{self.page_id}/posts", {"limit": limit})

    def create_post(self, message):
        if self.mock_mode:
            return {"id": "mock_post_created", "message": message}
        self._require_token()
        return self._request("POST", f"/{self.page_id}/feed", {"message": message})

    def get_comments(self, post_id, limit=25):
        if self.mock_mode:
            return {
                "data": [
                    {
                        "id": "mock_comment_1",
                        "from": {"id": "mock_user_1", "name": "Mock User"},
                        "message": "Shop oi gia bao nhieu?",
                    }
                ]
            }
        self._require_token()
        return self._request("GET", f"/{post_id}/comments", {"limit": limit})

    def reply_to_comment(self, comment_id, message):
        if self.mock_mode:
            return {"id": f"mock_reply_{comment_id}", "message": message}
        self._require_token()
        return self._request("POST", f"/{comment_id}/comments", {"message": message})

    def hide_comment(self, comment_id):
        if self.mock_mode:
            return {"success": True, "comment_id": comment_id, "is_hidden": True}
        self._require_token()
        return self._request("POST", f"/{comment_id}", {"is_hidden": "true"}, idempotent_hide=True)

    def _require_token(self):
        if not self.page_id or not self.page_access_token:
            raise FacebookAPIError(
                "FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN are required",
                status_code=401,
                retryable=False,
            )

    def _request(self, method, path, params, idempotent_hide=False):
        try:
            facebook_breaker.before_call()
        except CircuitOpen as exc:
            raise FacebookAPIError(str(exc), status_code=503, retryable=True) from exc

        params = dict(params or {})
        params["access_token"] = self.page_access_token
        endpoint = f"{self.base_url}{path}"
        encoded = urllib.parse.urlencode(params).encode("utf-8")
        url = endpoint
        data = None
        if method == "GET":
            url = f"{endpoint}?{encoded.decode('utf-8')}"
        else:
            data = encoded

        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        status_code = None
        response_text = ""
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status_code = response.status
                response_text = response.read().decode("utf-8")
                payload = json.loads(response_text or "{}")
                facebook_breaker.record_success()
                self._log(method, path, status_code, True, params, response_text)
                return payload
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            response_text = exc.read().decode("utf-8", errors="replace")
            if idempotent_hide and self._is_duplicate_spam_mark(response_text):
                facebook_breaker.record_success()
                self._log(
                    method,
                    path,
                    status_code,
                    True,
                    params,
                    response_text,
                    error="duplicate spam mark treated as success",
                )
                return {"success": True, "already_hidden": True}
            retryable = status_code >= 500 or status_code in {408, 429}
            if retryable:
                facebook_breaker.record_failure()
            self._log(method, path, status_code, False, params, response_text, retryable=retryable)
            message = self._error_message(response_text) or str(exc)
            raise FacebookAPIError(message, status_code=status_code, retryable=retryable) from exc
        except urllib.error.URLError as exc:
            facebook_breaker.record_failure()
            self._log(method, path, status_code, False, params, response_text, str(exc), retryable=True)
            raise FacebookAPIError(str(exc), status_code=503, retryable=True) from exc
        except TimeoutError as exc:
            facebook_breaker.record_failure()
            self._log(method, path, status_code, False, params, response_text, str(exc), retryable=True)
            raise FacebookAPIError("Facebook API timeout", status_code=504, retryable=True) from exc

    def _error_message(self, response_text):
        payload = self._error_payload(response_text)
        if not payload:
            return response_text[:500]
        error = payload.get("error", {})
        parts = [str(error.get("message") or "").strip()]
        if error.get("error_subcode"):
            parts.append(f"subcode={error.get('error_subcode')}")
        for key in ("error_user_title", "error_user_msg"):
            value = str(error.get(key) or "").strip()
            if value:
                parts.append(value)
        return " | ".join(part for part in parts if part) or response_text[:500]

    def _error_payload(self, response_text):
        try:
            return json.loads(response_text or "{}")
        except json.JSONDecodeError:
            return {}

    def _is_duplicate_spam_mark(self, response_text):
        error = self._error_payload(response_text).get("error", {})
        return error.get("error_subcode") == FACEBOOK_DUPLICATE_SPAM_MARK_SUBCODE

    def _log(self, method, endpoint, status_code, success, request_payload, response_text, error="", retryable=False):
        safe_payload = dict(request_payload or {})
        if "access_token" in safe_payload:
            safe_payload["access_token"] = "***"
        try:
            FacebookRequestLog.objects.create(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                success=success,
                retryable=retryable,
                request_preview=json.dumps(safe_payload, ensure_ascii=True)[:1000],
                response_preview=(response_text or "")[:2000],
                error_message=(error or "")[:2000],
            )
        except Exception:
            logger.exception("failed to persist facebook request log")
