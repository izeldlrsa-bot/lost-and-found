from django.urls import path

from . import views

app_name = "items"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────
    path("", views.item_list, name="item_list"),
    path("item/<uuid:pk>/", views.item_detail, name="item_detail"),

    # ── QR Handshake ──────────────────────────────────────────────────────
    path("handshake/<uuid:handshake_uuid>/", views.item_handshake, name="item_handshake"),

    # ── Authenticated item CRUD ───────────────────────────────────────────
    path("item/new/", views.item_create, name="item_create"),
    path("item/<uuid:pk>/edit/", views.item_edit, name="item_edit"),
    path("item/<uuid:pk>/delete/", views.item_delete, name="item_delete"),

    # ── Claims ────────────────────────────────────────────────────────────
    path("item/<uuid:item_pk>/claim/", views.claim_create, name="claim_create"),
    path("claim/<uuid:pk>/", views.claim_detail, name="claim_detail"),
    path("claim/<uuid:pk>/<str:action>/", views.claim_respond, name="claim_respond"),

    # ── Chat API (AJAX) ──────────────────────────────────────────────────
    path("api/claim/<uuid:pk>/messages/", views.api_messages, name="api_messages"),
    path("api/claim/<uuid:pk>/send/", views.api_send_message, name="api_send_message"),

    # ── Dashboards ────────────────────────────────────────────────────────
    path("my/items/", views.my_items, name="my_items"),
    path("my/claims/", views.my_claims, name="my_claims"),
]
