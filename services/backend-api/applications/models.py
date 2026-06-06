from django.db import models


class EventRecord(models.Model):
    STATUS_RECEIVED = "received"
    STATUS_PROCESSED = "processed"
    STATUS_REPLIED = "replied"
    STATUS_FAILED = "failed"
    STATUS_PENDING_REVIEW = "pending_review"

    event_id = models.CharField(max_length=160, unique=True)
    event_type = models.CharField(max_length=40)
    facebook_user_id = models.CharField(max_length=120, blank=True)
    facebook_user_name = models.CharField(max_length=255, blank=True)
    post_id = models.CharField(max_length=120, blank=True)
    comment_id = models.CharField(max_length=120, blank=True)
    message_id = models.CharField(max_length=120, blank=True)
    message = models.TextField(blank=True)
    intent = models.CharField(max_length=60, blank=True)
    sentiment = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=40, default=STATUS_RECEIVED)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["comment_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.event_id}"


class IdempotencyKey(models.Model):
    STATUS_PROCESSING = "processing"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"

    command_id = models.CharField(max_length=160, primary_key=True)
    event_id = models.CharField(max_length=160, blank=True)
    action = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=30, default=STATUS_PROCESSING)
    response = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.command_id}:{self.status}"


class FacebookRequestLog(models.Model):
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    retryable = models.BooleanField(default=False)
    request_preview = models.TextField(blank=True)
    response_preview = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["success", "created_at"])]


class BlacklistedUser(models.Model):
    facebook_user_id = models.CharField(max_length=120, unique=True)
    reason = models.CharField(max_length=255)
    violation_count = models.PositiveIntegerField(default=1)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self):
        return self.facebook_user_id


class ProcessingError(models.Model):
    event_id = models.CharField(max_length=160, blank=True)
    command_id = models.CharField(max_length=160, blank=True)
    topic = models.CharField(max_length=120, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    error_type = models.CharField(max_length=120, blank=True)
    error_message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
