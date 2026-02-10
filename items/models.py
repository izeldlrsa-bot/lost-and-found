"""
Core domain models for the Privacy-First Lost & Found system.

Item  – a found object reported by a finder.
Claim – a seeker's "proof of ownership" request linked to an item's UUID.
Message – anonymous chat messages scoped to a Claim (no PII exchanged).
"""
import base64
import io
import uuid

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse


# ═══════════════════════════════════════════════════════════════════════════════
# Item
# ═══════════════════════════════════════════════════════════════════════════════

class Category(models.TextChoices):
    ELECTRONICS = "electronics", "Electronics"
    CLOTHING = "clothing", "Clothing"
    DOCUMENTS = "documents", "Documents / IDs"
    KEYS = "keys", "Keys"
    BAGS = "bags", "Bags & Wallets"
    PETS = "pets", "Pets"
    JEWELRY = "jewelry", "Jewelry"
    OTHER = "other", "Other"


class ItemStatus(models.TextChoices):
    FOUND = "found", "Found"
    CLAIMED = "claimed", "Claimed"
    RETURNED = "returned", "Returned"


class Item(models.Model):
    """A found item posted by a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="found_items",
    )

    # ── Descriptors ───────────────────────────────────────────────────────
    title = models.CharField(max_length=120)
    description = models.TextField(help_text="Describe the item without revealing too many details publicly.")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    image = models.ImageField(upload_to="items/%Y/%m/", blank=True)

    # ── Location (neighbourhood-level only) ───────────────────────────────
    neighborhood = models.CharField(
        max_length=100,
        help_text="General area where the item was found (e.g. 'Downtown', 'West End').",
    )
    city = models.CharField(max_length=100, default="Unknown")

    # ── Status & Handshake ────────────────────────────────────────────────
    status = models.CharField(max_length=12, choices=ItemStatus.choices, default=ItemStatus.FOUND)
    handshake_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to="qrcodes/", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("items:item_detail", kwargs={"pk": self.pk})

    def get_handshake_url(self):
        return reverse("items:item_handshake", kwargs={"handshake_uuid": self.handshake_uuid})

    # ── QR generation ─────────────────────────────────────────────────────
    def _get_qr_base_url(self, request=None):
        """Resolve the public base URL for QR links."""
        from django.conf import settings as app_settings

        render_host = getattr(app_settings, "RENDER_EXTERNAL_HOSTNAME", "") or ""
        lan = getattr(app_settings, "LAN_HOST", "") or ""

        if render_host:
            return f"https://{render_host}"
        elif lan:
            return f"http://{lan}"
        elif request:
            return request.build_absolute_uri("/")[:-1]
        return "http://localhost:8000"

    def _make_qr_png_bytes(self, request=None):
        """Return raw PNG bytes for the handshake QR code."""
        link = f"{self._get_qr_base_url(request)}{self.get_handshake_url()}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @property
    def qr_code_data_uri(self):
        """Return a base64 data-URI for the QR code (no filesystem needed)."""
        png_bytes = self._make_qr_png_bytes()
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def generate_qr_code(self, request=None):
        """Create a QR code PNG and save it to the qr_code ImageField."""
        png_bytes = self._make_qr_png_bytes(request)
        filename = f"qr_{self.handshake_uuid}.png"
        self.qr_code.save(filename, ContentFile(png_bytes), save=False)

    def save(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        if not self.qr_code:
            self.generate_qr_code(request=request)
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# Claim
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Claim(models.Model):
    """A seeker's proof-of-ownership request against a found item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="claims")
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claims",
    )

    proof_of_ownership = models.TextField(
        help_text="Describe unique details only the true owner would know.",
    )
    status = models.CharField(max_length=10, choices=ClaimStatus.choices, default=ClaimStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "seeker"],
                name="unique_claim_per_seeker_per_item",
            )
        ]

    def __str__(self):
        return f"Claim by {self.seeker} on {self.item.title}"

    def get_absolute_url(self):
        return reverse("items:claim_detail", kwargs={"pk": self.pk})


# ═══════════════════════════════════════════════════════════════════════════════
# Anonymous Message (chat scoped to a Claim)
# ═══════════════════════════════════════════════════════════════════════════════

class Message(models.Model):
    """A single chat message inside a Claim thread — fully anonymous."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg {str(self.id)[:8]} in claim {str(self.claim_id)[:8]}"


# ═══════════════════════════════════════════════════════════════════════════════
# Notification
# ═══════════════════════════════════════════════════════════════════════════════

class Notification(models.Model):
    """A lightweight in-app notification for finders."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notif → {self.recipient} : {self.message[:40]}"
