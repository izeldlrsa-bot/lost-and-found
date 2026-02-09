from django import forms

from .models import Claim, Item, Message


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ("title", "description", "category", "image", "neighborhood", "city")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Black leather wallet"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe the item — avoid revealing serial numbers or unique marks publicly.",
                }
            ),
            "neighborhood": forms.TextInput(attrs={"placeholder": "e.g. West End, Central Park area"}),
            "city": forms.TextInput(attrs={"placeholder": "e.g. New York"}),
        }


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ("proof_of_ownership",)
        widgets = {
            "proof_of_ownership": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Describe unique details only the true owner would know (colour inside, scratches, contents, etc.).",
                }
            ),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Type a message…"}
            ),
        }
