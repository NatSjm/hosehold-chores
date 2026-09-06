# Household Chores — Implementation Plan

## Context

Homework: a tool for managing shared household chores. Scope was pinned down in
[SCOPE.md](SCOPE.md) — housemates each sign in on their own device, chores rotate
through a fixed order, and each chore becomes due again a fixed number of days **after it was last
completed**. Overdue chores simply sit there, visibly late, assigned to the same person until they
do them: no skipping, no auto-advance, no background scheduler.

The final open question is now settled: **only the current assignee may mark a chore done.** That
single rule keeps the completion log unambiguous and gives every mutating view exactly one
permission check.

Nothing exists yet — this is a greenfield Django project.

## Stack

- Python 3.12, Django 5.x, SQLite
- Server-rendered Django templates, `django.contrib.auth` for login/logout
- No JS framework, no REST API, no Celery/cron — the model needs none
- Plain CSS in one stylesheet, mobile-first (everyone uses their phone)

## Layout

```
C:\projects\household-chores\
  manage.py
  requirements.txt
  config/            # settings, urls, wsgi
  chores/
    models.py  forms.py  views.py  services.py  urls.py  admin.py
    templates/chores/   # base, dashboard, chore_detail, manage, chore_form
    templates/registration/login.html
    tests/  test_rotation.py  test_permissions.py  test_views.py
  static/css/app.css
```

Business rules live in `chores/services.py`, not in views — the rotation step is the one piece
worth unit-testing in isolation.

## Data model (`chores/models.py`)

- **Household** — `name`, `invite_code` (unique, 8 chars, generated on save), `created_at`
- **Membership** — `user` (OneToOne → `auth.User`), `household` (FK), `rotation_position` (int),
  `is_admin` (bool), `joined_at`; `Meta.ordering = ["rotation_position"]`, unique together
  `(household, rotation_position)` is *not* enforced (reordering would fight it) — positions are
  just a sort key
- **Chore** — `household` (FK), `name`, `interval_days` (PositiveInteger), `current_assignee`
  (FK → Membership, `on_delete=PROTECT`), `due_on` (DateField), `is_active` (bool), `created_at`
- **Completion** — `chore` (FK, `related_name="completions"`), `completed_by` (FK → `auth.User`,
  `on_delete=SET_NULL`, null), `completed_at` (auto_now_add); `Meta.ordering = ["-completed_at"]`

One user belongs to one household (OneToOne on Membership) — deliberately simple.
`Chore.is_overdue` is a property (`due_on < date.today()`), never a stored field.

## Core logic (`chores/services.py`)

```python
def next_membership(household, current):   # wraps around rotation_position
def complete_chore(chore, user):           # the one state transition
def reorder_rotation(household, ordered_membership_ids):
def rotate_off(membership):                # reassign chores before removing a member
```

`complete_chore` in a single `transaction.atomic()` block with `select_for_update()` on the chore:

1. Raise `PermissionDenied` if `chore.current_assignee.user != user` — **the assignee-only rule**.
2. Create the `Completion` row.
3. `chore.current_assignee = next_membership(...)` (next by `rotation_position`, wrapping to the
   lowest; falls back to the same person if they are the only member).
4. `chore.due_on = date.today() + timedelta(days=chore.interval_days)`.

New chores: admin picks the starting assignee; `due_on = today + interval_days`.

## Views & URLs (`chores/views.py`)

| URL | View | Access |
|---|---|---|
| `/accounts/login/`, `/accounts/logout/` | Django auth views | anyone |
| `/signup/` | `signup` — create a household **or** join with an invite code | anonymous |
| `/` | `dashboard` — chores by `due_on`, overdue flagged, "yours" flagged | member |
| `/chores/<pk>/` | `chore_detail` — interval, assignee, completion history | member |
| `/chores/<pk>/complete/` | `complete` — POST only, calls `complete_chore` | assignee |
| `/manage/` | `manage` — chore list, rotation order, invite code | admin |
| `/manage/chores/new/`, `/manage/chores/<pk>/edit/` | `chore_form` | admin |
| `/manage/rotation/` | `rotation` — POST new order | admin |

Two decorators in `chores/decorators.py`: `@member_required` (attaches `request.membership`) and
`@admin_required`. Only the assignee sees an enabled **Done** button; the view re-checks anyway.

Signup form: username, password, and either a household name (→ creates Household, `is_admin=True`,
`rotation_position=0`) or an invite code (→ joins, position = `max + 1`).

## Templates

`base.html` with a nav and `{% block %}`; `dashboard.html` as a card list — chore name, assignee,
due date, an `overdue` CSS class, and a `<form method="post">` Done button rendered only for the
assignee. `chore_detail.html` shows the completion table. `manage.html` shows the invite code, chore
table with edit links, and a rotation list with up/down buttons posting a reordered id list.

## Tests (`chores/tests/`)

- `test_rotation.py` — completion advances to the next member; wraps from last to first;
  single-member household stays put; `due_on` = today + interval; a `Completion` row is written
- `test_permissions.py` — non-assignee POST to `/complete/` → 403 and no state change; non-admin
  GET `/manage/` → 403; anonymous → redirected to login
- `test_views.py` — signup creates a household; signup with a valid code joins it; bad code is a
  form error; dashboard lists only the caller's household chores

## Milestones

1. Project skeleton + settings + `requirements.txt` — `python manage.py check` passes
2. Models + migrations + admin registration
3. `services.py` + `test_rotation.py` — logic green before any UI
4. Auth, signup/join flow, decorators
5. Dashboard, chore detail, complete view + `test_permissions.py`
6. Admin manage screens (chore CRUD, rotation reorder)
7. CSS pass, README with setup steps, full `manage.py test`

## Verification

```bash
python manage.py test
python manage.py runserver
```

End-to-end by hand: sign up as Anna creating "Flat 3" → copy the invite code → in a private window
sign up as Ben with that code → as Anna (admin) create "Dishes", interval 2 days, assignee Anna →
Anna's dashboard shows a Done button, Ben's does not → Anna marks it done → the chore moves to Ben
with `due_on` two days out, and the detail page logs Anna's completion → back-date `due_on` in the
Django admin and confirm it renders as overdue while staying with Ben.

## Assumptions

- Removing a member reassigns their open chores to the next person in the rotation
- Archiving a chore (`is_active=False`) hides it from the dashboard but keeps its history
- The admin can regenerate the invite code
- Explicitly out: fairness stats, notifications, swaps/skips, one-off tasks, weekday schedules,
  multi-household users, any API
