# Household Chores — Scope

A Django web app where housemates share a rotating set of recurring chores.

## Decided

| Axis | Decision |
|---|---|
| Users | Multi-user, each on their own device, real accounts |
| Assignment | Rotation — fixed order, cycles automatically |
| Recurrence | Interval **after completion** (`done` → next due = now + N days) |
| Overdue | Shown as overdue, stays with the assignee. No skip, no auto-advance |
| Joining | Invite code, entered at signup |
| History | Completion log: who did what, when |
| Permissions | Household creator (admin) manages chores; members view + complete |
| Stack | Django, server-rendered templates, `django.contrib.auth` |

## Data model

- **Household** — `name`, `invite_code` (unique), `created_at`
- **Membership** — `user`, `household`, `rotation_position` (int), `is_admin`, `joined_at`
- **Chore** — `household`, `name`, `interval_days`, `current_assignee` (→ Membership), `due_on`, `is_active`
- **Completion** — `chore`, `completed_by` (→ User), `completed_at`

One user belongs to one household (keeps it simple; multi-household is out).

## Core rule

Marking a chore done, in one transaction:
1. Write a `Completion` row.
2. `current_assignee` = next `Membership` by `rotation_position`, wrapping to the start.
3. `due_on` = today + `interval_days`.

Overdue = `due_on < today`. Purely a display state — no background job, no scheduler, nothing to run.

## Screens

1. **Signup / login** — signup takes an invite code, or creates a new household.
2. **Household dashboard** — all chores, sorted by due date, overdue highlighted, "mine" marked. Mark-done button.
3. **Chore detail** — interval, current assignee, completion history for that chore.
4. **Manage** (admin only) — add/edit/archive chores, reorder the rotation, view the invite code.

## Out of scope

Fairness stats · notifications (email/push) · swap or skip requests · one-off tasks · calendar-based schedules ("every Monday") · manual or points-based assignment · multi-household users · mobile app · public API

## Assumptions to confirm

- Removing a member reassigns their open chores to the next person in the rotation.
- Archiving a chore keeps its completion history.
- Invite code is regenerable by the admin.
