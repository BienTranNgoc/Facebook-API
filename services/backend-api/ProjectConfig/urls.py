from django.contrib import admin
from django.urls import path

from applications import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", views.health, name="health"),
    path("posts", views.posts, name="posts"),
    path("post", views.create_post, name="create_post"),
    path("comments", views.comments, name="comments"),
    path("events", views.events, name="events"),
    path("errors", views.processing_errors, name="processing_errors"),
    path("commands/process", views.process_command, name="process_command"),
    path("commands/<str:command_id>", views.command_status, name="command_status"),
]
