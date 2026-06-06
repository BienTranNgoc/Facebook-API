import json
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import EventRecord, IdempotencyKey

@override_settings(FACEBOOK_API_MODE="mock", KAFKA_ENABLED=False)
class ViewTests(TestCase):
    def test_health_check(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "ok")

    def test_events_list(self):
        EventRecord.objects.create(event_id="e1", event_type="comment", status="received")
        response = self.client.get(reverse("events"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["items"]), 1)

    def test_events_list_filter(self):
        EventRecord.objects.create(event_id="e1", event_type="comment", status="processed")
        EventRecord.objects.create(event_id="e2", event_type="comment", status="received")
        response = self.client.get(reverse("events") + "?status=processed")
        self.assertEqual(len(response.json()["data"]["items"]), 1)
        self.assertEqual(response.json()["data"]["items"][0]["event_id"], "e1")

    def test_command_status_not_found(self):
        response = self.client.get(reverse("command_status", kwargs={"command_id": "nonexistent"}))
        self.assertEqual(response.status_code, 404)

    def test_command_status_found(self):
        IdempotencyKey.objects.create(command_id="c1", status="success")
        response = self.client.get(reverse("command_status", kwargs={"command_id": "c1"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "success")

    def test_comments_requires_post_id(self):
        response = self.client.get(reverse("comments"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("post_id is required", response.json()["error"]["message"])

    @override_settings(DASHBOARD_API_TOKEN="test-token")
    def test_process_command_unauthorized(self):
        response = self.client.post(reverse("process_command"), data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @override_settings(DASHBOARD_API_TOKEN="test-token")
    def test_process_command_authorized(self):
        response = self.client.post(
            reverse("process_command"), 
            data=json.dumps({"command_id": "c1", "action": "noop"}), 
            content_type="application/json",
            HTTP_X_ADMIN_TOKEN="test-token"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
