import secrets
from datetime import date

from django.conf import settings
from django.db import models

# Codes are read off one phone and typed into another, so drop the glyphs that
# look alike: 0/O, 1/I/L.
INVITE_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 8


def generate_invite_code():
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


class Household(models.Model):
    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=INVITE_CODE_LENGTH, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self.new_invite_code()
        super().save(*args, **kwargs)

    @classmethod
    def new_invite_code(cls):
        """A code no other household is using."""
        while True:
            code = generate_invite_code()
            if not cls.objects.filter(invite_code=code).exists():
                return code


class Membership(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    rotation_position = models.PositiveIntegerField(default=0)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Positions are a sort key only — duplicates are allowed so that a
        # reorder does not have to fight a uniqueness constraint.
        ordering = ["rotation_position"]

    def __str__(self):
        return f"{self.user} in {self.household}"


class Chore(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    name = models.CharField(max_length=100)
    interval_days = models.PositiveIntegerField()
    current_assignee = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="assigned_chores"
    )
    due_on = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_on"]

    def __str__(self):
        return self.name

    @property
    def is_overdue(self):
        return self.due_on < date.today()


class Completion(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="completions")
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.chore} by {self.completed_by} on {self.completed_at:%Y-%m-%d}"
