from django.urls import path

from . import views

urlpatterns = [
    path("", views.chore_list, name="chore_list"),
    path("roommates", views.roommate_list, name="roommate_list"),
    path(
        "roommates/<int:pk>/delete",
        views.roommate_delete,
        name="roommate_delete",
    ),
    path("chores/new", views.chore_create, name="chore_create"),
    path("chores/<int:pk>/done", views.chore_done, name="chore_done"),
    path("chores/<int:pk>/reopen", views.chore_reopen, name="chore_reopen"),
    path("recurring/new", views.recurring_create, name="recurring_create"),
    path(
        "recurring/<int:pk>/delete",
        views.recurring_delete,
        name="recurring_delete",
    ),
]
