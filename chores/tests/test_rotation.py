from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from chores.models import Chore, Household, Membership
from chores.services import complete_chore, next_membership


def make_household(name, *usernames):
    """A household whose members sit at rotation positions 0, 1, 2, ..."""
    household = Household.objects.create(name=name)
    memberships = [
        Membership.objects.create(
            user=User.objects.create_user(username),
            household=household,
            rotation_position=position,
        )
        for position, username in enumerate(usernames)
    ]
    return household, memberships


class NextMembershipTests(TestCase):
    def test_advances_to_the_next_position(self):
        household, (anna, ben, cara) = make_household("Flat 3", "anna", "ben", "cara")

        self.assertEqual(next_membership(household, anna), ben)
        self.assertEqual(next_membership(household, ben), cara)

    def test_wraps_from_last_to_first(self):
        household, (anna, ben, cara) = make_household("Flat 3", "anna", "ben", "cara")

        self.assertEqual(next_membership(household, cara), anna)

    def test_single_member_stays_put(self):
        household, (solo,) = make_household("Studio", "solo")

        self.assertEqual(next_membership(household, solo), solo)


class CompleteChoreTests(TestCase):
    def setUp(self):
        self.household, (self.anna, self.ben) = make_household("Flat 3", "anna", "ben")
        self.chore = Chore.objects.create(
            household=self.household,
            name="Dishes",
            interval_days=2,
            current_assignee=self.anna,
            due_on=date.today() - timedelta(days=1),
        )

    def test_completion_hands_the_chore_to_the_next_member(self):
        complete_chore(self.chore, self.anna.user)

        self.chore.refresh_from_db()
        self.assertEqual(self.chore.current_assignee, self.ben)

    def test_completion_in_a_single_member_household_stays_put(self):
        household, (solo,) = make_household("Studio", "solo")
        chore = Chore.objects.create(
            household=household,
            name="Bins",
            interval_days=7,
            current_assignee=solo,
            due_on=date.today(),
        )

        complete_chore(chore, solo.user)

        chore.refresh_from_db()
        self.assertEqual(chore.current_assignee, solo)

    def test_due_on_is_today_plus_the_interval(self):
        complete_chore(self.chore, self.anna.user)

        self.chore.refresh_from_db()
        self.assertEqual(self.chore.due_on, date.today() + timedelta(days=2))

    def test_a_completion_row_is_written(self):
        complete_chore(self.chore, self.anna.user)

        completion = self.chore.completions.get()
        self.assertEqual(completion.completed_by, self.anna.user)

    def test_only_the_assignee_may_complete(self):
        with self.assertRaises(PermissionDenied):
            complete_chore(self.chore, self.ben.user)

        self.chore.refresh_from_db()
        self.assertEqual(self.chore.current_assignee, self.anna)
        self.assertEqual(self.chore.completions.count(), 0)
