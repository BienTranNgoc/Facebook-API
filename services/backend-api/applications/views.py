import json
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .facebook_client import FacebookAPIError, FacebookClient
from .models import EventRecord, IdempotencyKey, ProcessingError
from .services import CommandProcessor


def api_response(data=None, status=200, error=None):
    payload = {"ok": error is None}
    if error is not None:
        payload["error"] = error
    else:
        payload["data"] = data if data is not None else {}
    return JsonResponse(payload, status=status)


def parse_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise ValueError("invalid JSON body")


def admin_token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        expected = settings.DASHBOARD_API_TOKEN
        if expected:
            provided = request.headers.get("X-Admin-Token") or request.headers.get("Authorization", "").removeprefix("Bearer ")
            if provided != expected:
                return api_response(status=401, error={"code": "unauthorized", "message": "admin token is required"})
        return view_func(request, *args, **kwargs)

    return wrapper


def handle_facebook_error(exc):
    status = exc.status_code if exc.status_code in {400, 401, 403, 404, 409, 429, 500, 502, 503, 504} else 502
    return api_response(status=status, error={"code": "facebook_api_error", **exc.as_dict()})


@require_GET
def health(request):
    return api_response({"service": "backend-api", "status": "ok"})


@require_GET
def posts(request):
    limit = int(request.GET.get("limit", "25"))
    try:
        return api_response(FacebookClient().list_posts(limit=limit))
    except FacebookAPIError as exc:
        return handle_facebook_error(exc)


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def create_post(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return api_response(status=400, error={"code": "invalid_json", "message": str(exc)})
    message = (payload.get("message") or "").strip()
    if not message:
        return api_response(status=400, error={"code": "validation_error", "message": "message is required"})
    try:
        return api_response(FacebookClient().create_post(message), status=201)
    except FacebookAPIError as exc:
        return handle_facebook_error(exc)


@require_GET
def comments(request):
    post_id = request.GET.get("post_id")
    if not post_id:
        return api_response(status=400, error={"code": "validation_error", "message": "post_id is required"})
    limit = int(request.GET.get("limit", "25"))
    try:
        return api_response(FacebookClient().get_comments(post_id, limit=limit))
    except FacebookAPIError as exc:
        return handle_facebook_error(exc)


@require_GET
def events(request):
    status_filter = request.GET.get("status")
    queryset = EventRecord.objects.all()
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    data = [
        {
            "event_id": item.event_id,
            "event_type": item.event_type,
            "post_id": item.post_id,
            "comment_id": item.comment_id,
            "message_id": item.message_id,
            "message": item.message,
            "intent": item.intent,
            "sentiment": item.sentiment,
            "action": item.action,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in queryset[:100]
    ]
    return api_response({"items": data})


@require_GET
def command_status(request, command_id):
    try:
        item = IdempotencyKey.objects.get(command_id=command_id)
    except IdempotencyKey.DoesNotExist:
        return api_response(status=404, error={"code": "not_found", "message": "command not found"})
    return api_response(
        {
            "command_id": item.command_id,
            "event_id": item.event_id,
            "action": item.action,
            "status": item.status,
            "response": item.response,
            "processed_at": item.processed_at.isoformat() if item.processed_at else None,
        }
    )


@csrf_exempt
@admin_token_required
@require_http_methods(["POST"])
def process_command(request):
    try:
        command = parse_json_body(request)
        result = CommandProcessor().process(command)
    except ValueError as exc:
        return api_response(status=400, error={"code": "validation_error", "message": str(exc)})
    except FacebookAPIError as exc:
        return handle_facebook_error(exc)
    return api_response(result)


@require_GET
def processing_errors(request):
    data = [
        {
            "event_id": item.event_id,
            "command_id": item.command_id,
            "topic": item.topic,
            "retry_count": item.retry_count,
            "error_type": item.error_type,
            "error_message": item.error_message,
            "created_at": item.created_at.isoformat(),
        }
        for item in ProcessingError.objects.all()[:100]
    ]
    return api_response({"items": data})
