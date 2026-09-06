from django.contrib import admin

from .models import Chore, Completion, Household, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["name", "invite_code", "created_at"]
    search_fields = ["name", "invite_code"]
    readonly_fields = ["created_at"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "household", "rotation_position", "is_admin", "joined_at"]
    list_filter = ["household", "is_admin"]
    list_editable = ["rotation_position"]
    search_fields = ["user__username"]
    readonly_fields = ["joined_at"]


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    # due_on is editable from the list so it can be back-dated during the
    # end-to-end walkthrough without opening each chore.
    list_display = ["name", "household", "current_assignee", "interval_days", "due_on",
                    "is_active", "overdue"]
    list_editable = ["due_on", "is_active"]
    list_filter = ["household", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["created_at"]

    @admin.display(boolean=True, description="Overdue")
    def overdue(self, obj):
        return obj.is_overdue


@admin.register(Completion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = ["chore", "completed_by", "completed_at"]
    list_filter = ["chore__household", "completed_at"]
    search_fields = ["chore__name", "completed_by__username"]
    readonly_fields = ["completed_at"]
