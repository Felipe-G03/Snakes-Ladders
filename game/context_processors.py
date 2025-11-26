from .models import FriendRequest, RoomInvite

def header_notifications(request):
    if not request.user.is_authenticated:
        return {}

    friend_reqs = FriendRequest.objects.filter(
        addressee=request.user,
        status="pending",
    )

    room_invites = RoomInvite.objects.filter(
        invitee=request.user,
        status="pending",
    )

    total = friend_reqs.count() + room_invites.count()

    return {
        "header_friend_requests": friend_reqs,
        "header_room_invites": room_invites,
        "header_notifications_count": total,
    }
