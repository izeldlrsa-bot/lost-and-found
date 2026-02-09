"""
Privacy-focused custom User model.

The `masked_email` property lets the UI show 'j***n@g***.com' instead of the
real address, so even in admin / templates personal data is never leaked.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user that adds a public alias and masks PII by default."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(
        max_length=60,
        blank=True,
        help_text="Public alias shown instead of your real name.",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    # ── Privacy helpers ───────────────────────────────────────────────────
    @property
    def masked_email(self) -> str:
        """Return an obfuscated version of the email, e.g. j***n@g***.com"""
        if not self.email or "@" not in self.email:
            return ""
        local, domain = self.email.split("@", 1)
        masked_local = local[0] + "***" + (local[-1] if len(local) > 1 else "")
        if "." in domain:
            domain_name, domain_ext = domain.rsplit(".", 1)
            masked_domain = domain_name[0] + "***" + "." + domain_ext
        else:
            masked_domain = domain[0] + "***"
        return f"{masked_local}@{masked_domain}"

    @property
    def public_name(self) -> str:
        return self.display_name or f"user-{str(self.id)[:8]}"

    def __str__(self):
        return self.public_name
