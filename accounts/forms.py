from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class SignUpForm(UserCreationForm):
    display_name = forms.CharField(
        max_length=60,
        required=False,
        help_text="A public alias. Leave blank for an auto-generated one.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name", "password1", "password2")
