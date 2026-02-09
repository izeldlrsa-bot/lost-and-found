"""
Core domain models for the Privacy-First Lost & Found system.

Item  – a found object reported by a finder.
Claim – a seeker's "proof of ownership" request linked to an item's UUID.
Message – anonymous chat messages scoped to a Claim (no PII exchanged).
"""
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
    def generate_qr_code(self, request=None):
        """Create a QR code PNG that encodes the handshake URL."""
        from django.conf import settings as app_settings

        lan = getattr(app_settings, "LAN_HOST", "")
        if lan:
            base = f"http://{lan}"
        elif request:
            base = request.build_absolute_uri("/")[:-1]
        else:
            base = "http://localhost:8000"

        link = f"{base}{self.get_handshake_url()}"

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        filename = f"qr_{self.handshake_uuid}.png"
        self.qr_code.save(filename, ContentFile(buf.getvalue()), save=False)

    def save(self, *args, **kwargs):
        # Generate QR on first save (no qr_code yet)
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
