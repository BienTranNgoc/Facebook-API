from django.contrib import admin

from .models import (
    BlacklistedUser,
    EventRecord,
    FacebookRequestLog,
    IdempotencyKey,
    ProcessingError,
)


@admin.register(EventRecord)
class EventRecordAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "sentiment", "intent", "action", "status")
    search_fields = ("event_id", "comment_id", "message", "facebook_user_id")
    list_filter = ("event_type", "sentiment", "intent", "action", "status")


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("command_id", "event_id", "action", "status", "processed_at")
    search_fields = ("command_id", "event_id")
    list_filter = ("status", "action")


@admin.register(FacebookRequestLog)
class FacebookRequestLogAdmin(admin.ModelAdmin):
    list_display = ("method", "endpoint", "status_code", "success", "retryable", "created_at")
    search_fields = ("endpoint", "error_message", "response_preview")
    list_filter = ("success", "retryable", "method")


@admin.register(BlacklistedUser)
class BlacklistedUserAdmin(admin.ModelAdmin):
    list_display = ("facebook_user_id", "reason", "violation_count", "last_seen_at")
    search_fields = ("facebook_user_id", "reason")


@admin.register(ProcessingError)
class ProcessingErrorAdmin(admin.ModelAdmin):
    list_display = ("event_id", "command_id", "topic", "retry_count", "error_type", "created_at")
    search_fields = ("event_id", "command_id", "error_message")
