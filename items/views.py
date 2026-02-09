"""
Views for the Items app.

Privacy guarantee: real emails / names are never exposed in any template
context. The user's `public_name` and `masked_email` are used everywhere.
"""
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ClaimForm, ItemForm, MessageForm
from .models import Claim, ClaimStatus, Item, ItemStatus, Message


# ═══════════════════════════════════════════════════════════════════════════════
# Item views
# ═══════════════════════════════════════════════════════════════════════════════

def item_list(request):
    """Public listing of all currently-found items."""
    queryset = Item.objects.filter(status=ItemStatus.FOUND)

    # Simple search / filter
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(neighborhood__icontains=q)
        )
    if category:
        queryset = queryset.filter(category=category)

    return render(request, "items/item_list.html", {
        "items": queryset,
        "search_query": q,
        "selected_category": category,
    })


def item_detail(request, pk):
    """Detail view for a single item (public)."""
    item = get_object_or_404(Item, pk=pk)
    # Regenerate QR if missing (e.g. after IP change)
    if not item.qr_code:
        item.save(request=request)

    # If the viewer is the finder, show all claims so they can review & chat
    claims = None
    if request.user.is_authenticated and request.user == item.finder:
        claims = item.claims.select_related("seeker").all()

    return render(request, "items/item_detail.html", {"item": item, "claims": claims})


@login_required
def item_create(request):
    """Authenticated user reports a found item."""
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.finder = request.user
            item.save(request=request)
            django_messages.success(request, "Item posted! Share the QR code so the owner can claim it.")
            return redirect(item.get_absolute_url())
    else:
        form = ItemForm()
    return render(request, "items/item_create.html", {"form": form})


@login_required
def item_edit(request, pk):
    """Only the finder can edit their own post."""
    item = get_object_or_404(Item, pk=pk, finder=request.user)
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save(request=request)
            django_messages.success(request, "Item updated.")
            return redirect(item.get_absolute_url())
    else:
        form = ItemForm(instance=item)
    return render(request, "items/item_edit.html", {"form": form, "item": item})


@login_required
def item_delete(request, pk):
    """Only the finder can delete their post."""
    item = get_object_or_404(Item, pk=pk, finder=request.user)
    if request.method == "POST":
        item.delete()
        django_messages.success(request, "Item removed.")
        return redirect("items:item_list")
    return render(request, "items/item_confirm_delete.html", {"item": item})


# ═══════════════════════════════════════════════════════════════════════════════
# QR Handshake entry-point
# ═══════════════════════════════════════════════════════════════════════════════

def item_handshake(request, handshake_uuid):
    """
    Landing page reached by scanning the QR code.
    Redirects to the claim form so the seeker can submit proof of ownership.
    """
    item = get_object_or_404(Item, handshake_uuid=handshake_uuid)
    if item.status != ItemStatus.FOUND:
        django_messages.info(request, "This item has already been claimed or returned.")
    return redirect("items:claim_create", item_pk=item.pk)


# ═══════════════════════════════════════════════════════════════════════════════
# Claim views
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def claim_create(request, item_pk):
    """Seeker submits a proof-of-ownership claim."""
    item = get_object_or_404(Item, pk=item_pk)

    # Prevent the finder from claiming their own item
    if item.finder == request.user:
        django_messages.warning(request, "You cannot claim your own item.")
        return redirect(item.get_absolute_url())

    # One claim per seeker per item
    existing = Claim.objects.filter(item=item, seeker=request.user).first()
    if existing:
        django_messages.info(request, "You have already submitted a claim for this item.")
        return redirect(existing.get_absolute_url())

    if request.method == "POST":
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            claim.seeker = request.user
            claim.save()
            django_messages.success(request, "Claim submitted! The finder will review it.")
            return redirect(claim.get_absolute_url())
    else:
        form = ClaimForm()

    return render(request, "items/claim_create.html", {"form": form, "item": item})


@login_required
def claim_detail(request, pk):
    """
    View a claim + its anonymous chat thread.
    Only the finder or the seeker may view.
    """
    claim = get_object_or_404(Claim, pk=pk)

    if request.user not in (claim.seeker, claim.item.finder):
        raise Http404

    chat_messages = claim.messages.all()

    if request.method == "POST":
        msg_form = MessageForm(request.POST)
        if msg_form.is_valid():
            msg = msg_form.save(commit=False)
            msg.claim = claim
            msg.sender = request.user
            msg.save()
            return redirect(claim.get_absolute_url())
    else:
        msg_form = MessageForm()

    return render(request, "items/claim_detail.html", {
        "claim": claim,
        "chat_messages": chat_messages,
        "msg_form": msg_form,
    })


@login_required
@require_POST
def claim_respond(request, pk, action):
    """Finder approves or rejects a claim."""
    claim = get_object_or_404(Claim, pk=pk)

    if request.user != claim.item.finder:
        raise Http404

    if action == "approve":
        claim.status = ClaimStatus.APPROVED
        claim.item.status = ItemStatus.CLAIMED
        claim.item.save()
        django_messages.success(request, "Claim approved. Coordinate return via chat.")
    elif action == "reject":
        claim.status = ClaimStatus.REJECTED
        django_messages.info(request, "Claim rejected.")
    else:
        raise Http404

    claim.save()
    return redirect(claim.get_absolute_url())


@login_required
def my_items(request):
    """Dashboard showing items the current user has posted."""
    items = Item.objects.filter(finder=request.user)
    return render(request, "items/my_items.html", {"items": items})


@login_required
def my_claims(request):
    """Dashboard showing claims the current user has submitted."""
    claims = Claim.objects.filter(seeker=request.user).select_related("item")
    return render(request, "items/my_claims.html", {"claims": claims})


# ═══════════════════════════════════════════════════════════════════════════════
# Chat API (AJAX endpoints for real-time-like messaging)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def api_messages(request, pk):
    """Return messages for a claim as JSON. Supports ?after=<msg_id> for polling."""
    claim = get_object_or_404(Claim, pk=pk)
    if request.user not in (claim.seeker, claim.item.finder):
        return JsonResponse({"error": "forbidden"}, status=403)

    qs = claim.messages.select_related("sender").all()

    # If ?after=<uuid> is provided, only return newer messages
    after = request.GET.get("after")
    if after:
        try:
            last_msg = Message.objects.get(pk=after)
            qs = qs.filter(created_at__gt=last_msg.created_at)
        except Message.DoesNotExist:
            pass

    messages_data = [
        {
            "id": str(msg.id),
            "body": msg.body,
            "sender_name": msg.sender.public_name,
            "is_mine": msg.sender == request.user,
            "created_at": msg.created_at.isoformat(),
            "time_display": f"{msg.created_at.strftime('%I:%M %p')}",
        }
        for msg in qs
    ]
    return JsonResponse({"messages": messages_data})


@login_required
@require_POST
def api_send_message(request, pk):
    """Send a message via AJAX and return the new message as JSON."""
    claim = get_object_or_404(Claim, pk=pk)
    if request.user not in (claim.seeker, claim.item.finder):
        return JsonResponse({"error": "forbidden"}, status=403)

    body = request.POST.get("body", "").strip()
    if not body:
        return JsonResponse({"error": "empty message"}, status=400)

    msg = Message.objects.create(
        claim=claim,
        sender=request.user,
        body=body,
    )
    return JsonResponse({
        "id": str(msg.id),
        "body": msg.body,
        "sender_name": msg.sender.public_name,
        "is_mine": True,
        "created_at": msg.created_at.isoformat(),
        "time_display": f"{msg.created_at.strftime('%I:%M %p')}",
    })
