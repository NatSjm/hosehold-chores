# Household Chores — Backlog

Derived from [_docs/plan.md](_docs/plan.md) and [_docs/SCOPE.md](_docs/SCOPE.md).
Tasks are ordered; each is meant to be one commit and leaves the project runnable.

**Already in place:** `manage.py`, `config/` (settings, urls, wsgi, asgi), empty `chores/` app
registered in `INSTALLED_APPS`, `requirements.txt` pinning Django 5.2.

---

## Milestone 1 — Skeleton

### T1 — Finish project settings
Add `LOGIN_URL = "/accounts/login/"`, `LOGIN_REDIRECT_URL = "/"`, `LOGOUT_REDIRECT_URL = "/accounts/login/"`,
`STATICFILES_DIRS = [BASE_DIR / "static"]`, and `TIME_ZONE`. Create `static/css/app.css` (empty for now).
**Done when:** `python manage.py check` passes with no warnings.

## Milestone 2 — Data model

### T2 — Models
`Household` (name, unique 8-char `invite_code` generated on save, `created_at`),
`Membership` (OneToOne user, FK household, `rotation_position`, `is_admin`, `joined_at`,
`Meta.ordering = ["rotation_position"]`), `Chore` (household, name, `interval_days`,
`current_assignee` → Membership `PROTECT`, `due_on`, `is_active`, `created_at`, `is_overdue` property),
`Completion` (chore `related_name="completions"`, `completed_by` → User `SET_NULL`, `completed_at`,
`Meta.ordering = ["-completed_at"]`).
**Done when:** `makemigrations` + `migrate` run clean; `is_overdue` is a property, not a column.

### T3 — Admin registration
Register all four models with useful `list_display` / `list_filter` so `due_on` can be back-dated by hand
during verification.
**Done when:** all four models are editable at `/admin/`.

## Milestone 3 — Business logic (before any UI)

### T4 — `chores/services.py`
`next_membership(household, current)` — next by `rotation_position`, wrapping to the lowest, returning
`current` when they are the only member. `complete_chore(chore, user)` — one `transaction.atomic()`
with `select_for_update()`: raise `PermissionDenied` unless `chore.current_assignee.user == user`,
write the `Completion`, advance the assignee, set `due_on = today + interval_days`.
**Done when:** functions exist with no view or request imports.

### T5 — `chores/tests/test_rotation.py`
Completion advances to the next member; wraps last → first; single-member household stays put;
`due_on` is today + interval; a `Completion` row is written.
**Done when:** `python manage.py test chores.tests.test_rotation` is green.

## Milestone 4 — Auth and joining

### T6 — Login/logout + decorators
Wire `django.contrib.auth.urls` at `/accounts/`, add `templates/registration/login.html`, and write
`chores/decorators.py`: `@member_required` (attaches `request.membership`, redirects anonymous users to
login) and `@admin_required` (403 for non-admins).
**Done when:** a user created in the shell can log in and out.

### T7 — Signup / join flow
`SignupForm` (username, password, plus either a household name or an invite code — exactly one).
Creating: new `Household`, `is_admin=True`, `rotation_position=0`. Joining: look up the code,
`rotation_position = max + 1`; unknown code is a form error, not a crash.
**Done when:** `/signup/` creates a household and joins one with a code.

## Milestone 5 — Member screens

### T8 — Dashboard + chore detail
`base.html` with nav and blocks. `/` lists the caller's household's active chores by `due_on`, flags
overdue ones with a CSS class and marks "yours". `/chores/<pk>/` shows interval, assignee and the
completion table.
**Done when:** both pages render for a logged-in member and 404 on another household's chore.

### T9 — Complete view
`POST /chores/<pk>/complete/` calls `complete_chore` and redirects to the dashboard. The Done button
renders only for the assignee; the view re-checks regardless.
**Done when:** the assignee can complete a chore from the dashboard.

### T10 — `chores/tests/test_permissions.py`
Non-assignee POST to `/complete/` → 403 with no state change; non-admin GET `/manage/` → 403;
anonymous → redirect to login.
**Done when:** green.

## Milestone 6 — Admin screens

### T11 — Manage page + chore CRUD
`/manage/` shows the invite code, the chore table with edit links and the rotation order.
`/manage/chores/new/` and `/manage/chores/<pk>/edit/` use one `ChoreForm` (name, interval, starting
assignee, `is_active`); new chores get `due_on = today + interval_days`. Archiving is `is_active=False`,
which hides the chore from the dashboard but keeps its history.
**Done when:** an admin can add, edit and archive chores.

### T12 — Rotation reorder + member removal
`POST /manage/rotation/` accepts a reordered membership id list and rewrites `rotation_position`.
`rotate_off(membership)` reassigns that member's open chores to the next person before removal.
**Done when:** up/down buttons persist a new order and removing a member leaves no orphaned chores.

### T13 — Regenerate invite code
Admin-only POST that issues a fresh code for the household.
**Done when:** the old code no longer joins.

## Milestone 7 — Finish

### T14 — `chores/tests/test_views.py`
Signup creates a household; signup with a valid code joins it; a bad code is a form error; the dashboard
lists only the caller's household's chores.
**Done when:** green.

### T15 — CSS pass + README
Mobile-first `static/css/app.css` (card list, clear overdue state, tap-sized buttons). README with setup,
migrate, runserver and test commands.
**Done when:** the app is legible on a phone-width viewport.

### T16 — End-to-end walkthrough
Run the manual script from the plan: Anna creates "Flat 3" → Ben joins by code → Anna creates "Dishes"
(2 days, assigned to Anna) → only Anna sees Done → Anna completes → the chore moves to Ben, due in 2 days,
and the detail page logs Anna → back-date `due_on` in `/admin/` and confirm it shows overdue while staying
with Ben.
**Done when:** the full `python manage.py test` suite passes and the walkthrough matches.

---

## Out of scope (do not pick up)

Fairness stats · notifications · swap/skip requests · one-off tasks · weekday schedules · manual or
points-based assignment · multi-household users · REST API · background scheduler.
