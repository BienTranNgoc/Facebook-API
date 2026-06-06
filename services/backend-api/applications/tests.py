import io
import json
import urllib.error
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from .facebook_client import FacebookClient
from .models import IdempotencyKey
from .services import CommandProcessor


@override_settings(FACEBOOK_API_MODE="mock", KAFKA_ENABLED=False)
class BackendApiTests(TestCase):
    def test_posts_endpoint_uses_normalized_response(self):
        response = self.client.get("/posts")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload["data"])

    def test_process_command_is_idempotent(self):
        command = {
            "command_id": "cmd-1",
            "event_id": "event-1",
            "event_type": "comment",
            "action": "reply_comment",
            "target": {"comment_id": "comment-1"},
            "reply_text": "Thanks",
        }
        processor = CommandProcessor(facebook_client=FacebookClient())
        first = processor.process(command)
        second = processor.process(command)
        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate_skipped")
        self.assertEqual(IdempotencyKey.objects.count(), 1)

    def test_create_post_requires_message(self):
        response = self.client.post("/post", data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("applications.views.settings.DASHBOARD_API_TOKEN", "secret")
    def test_admin_token_is_enforced_when_configured(self):
        response = self.client.post(
            "/post",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


@override_settings(
    FACEBOOK_API_MODE="live",
    FACEBOOK_GRAPH_VERSION="v20.0",
    FACEBOOK_PAGE_ID="page-1",
    FACEBOOK_PAGE_ACCESS_TOKEN="token",
)
class FacebookClientLiveModeTests(SimpleTestCase):
    @patch.object(FacebookClient, "_log")
    @patch("applications.facebook_client.urllib.request.urlopen")
    def test_hide_comment_treats_duplicate_spam_mark_as_success(self, urlopen, log_mock):
        payload = json.dumps({
            "error": {
                "message": "An unknown error occurred",
                "error_subcode": 1446036,
            }
        })
        urlopen.side_effect = urllib.error.HTTPError(
            "https://graph.facebook.com/v20.0/comment-1",
            400,
            "Bad Request",
            {},
            io.BytesIO(payload.encode("utf-8")),
        )

        result = FacebookClient().hide_comment("comment-1")

        self.assertEqual(result, {"success": True, "already_hidden": True})
        log_mock.assert_called_once()
