"""Business rules for the chore rotation.

Deliberately free of view, request and template imports so the one state
transition in the app can be unit-tested on its own.
"""

from datetime import date, timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Chore, Completion


def next_membership(household, current):
    """The member after `current` in the rotation, wrapping round to the lowest.

    Returns `current` unchanged when they are the household's only member.
    """
    # rotation_position is not unique, so pk breaks ties and keeps the order stable.
    members = list(household.memberships.order_by("rotation_position", "pk"))
    if len(members) <= 1:
        return current

    ids = [m.pk for m in members]
    try:
        index = ids.index(current.pk)
    except ValueError:
        # `current` belongs to another household — start the rotation over.
        return members[0]
    return members[(index + 1) % len(members)]


def complete_chore(chore, user):
    """Mark `chore` done by `user`, then hand it to the next member.

    Only the current assignee may complete a chore; anyone else gets
    `PermissionDenied` and the chore is left untouched.
    """
    with transaction.atomic():
        chore = Chore.objects.select_for_update().get(pk=chore.pk)

        if chore.current_assignee.user_id != user.pk:
            raise PermissionDenied("Only the current assignee can complete this chore.")

        Completion.objects.create(chore=chore, completed_by=user)
        chore.current_assignee = next_membership(chore.household, chore.current_assignee)
        chore.due_on = date.today() + timedelta(days=chore.interval_days)
        chore.save(update_fields=["current_assignee", "due_on"])

    return chore
